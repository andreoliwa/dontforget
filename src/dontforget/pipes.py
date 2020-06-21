"""Pipes."""
import abc
import itertools
import json
import logging
import os
from enum import Enum
from pathlib import Path
from pprint import pprint
from typing import Dict, Iterator, List, Optional, Set, Tuple, Type, Union

import click
import toml
from autorepr import autorepr
from jinja2 import StrictUndefined, Template
from memoized_property import memoized_property

from dontforget.app import load_plugins
from dontforget.constants import DEFAULT_PIPES_DIR_NAME, UNIQUE_SEPARATOR
from dontforget.generic import (
    SingletonMixin,
    classproperty,
    find_partial_keys,
    flatten,
    get_subclasses,
    pretty_plugin_name,
    unflatten,
)
from dontforget.settings import LOG_LEVEL, USER_PIPES_DIR
from dontforget.typedefs import JsonDict

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(LOG_LEVEL)


class Pipe:
    """A pipe to pull data from a source and push to a target."""

    class Key(Enum):
        """TOML keys."""

        PIPES = "pipes"
        SOURCE = "source"
        TARGET = "target"
        CLASS = "class"

    __repr__ = autorepr(["name", "path"])

    def __init__(self, toml_file: Path):
        self.name = toml_file.stem
        self.path = toml_file.resolve()
        self.source_class_name: str = ""
        self.target_class_name: str = ""

    def __lt__(self, other):
        """Less than operator, case insensitive."""
        return self.name.casefold() < other.name.casefold()

    @memoized_property
    def original_dict(self) -> JsonDict:
        """Return the original dict."""

        return toml.loads(self.path.read_text())

    @memoized_property
    def merged_dict(self) -> JsonDict:
        """Return the original dict merged with the parent pipes."""
        return self.merge_parent_pipes()

    def echo(self):
        """Echo a pipe on the teminal."""
        click.secho(f"\n>>> {self.name} @ {self.path}", fg="bright_white")
        self.echo_dict()

    def echo_dict(self):
        """Pretty print the pipe structure as a dict."""
        pprint(self.merged_dict)
        # TODO: option --json or --style json|pprint|toml
        # print(json.dumps(self.merged_dict, indent=2, sort_keys=True))

    def merge_parent_pipes(self) -> JsonDict:
        """Merge parent pipes (first) into this pipe (last)."""
        original_without_pipes: JsonDict = self.original_dict.copy()
        parent_pipes: List[str] = original_without_pipes.pop(self.Key.PIPES.value, [])
        if not parent_pipes:
            return original_without_pipes

        rv: JsonDict = {}
        for name in parent_pipes:
            parent_pipe = PIPE_CONFIG.get_pipe(name)
            rv.update(flatten(parent_pipe.original_dict, separator=UNIQUE_SEPARATOR))

        rv.update(flatten(original_without_pipes, separator=UNIQUE_SEPARATOR))

        return unflatten(rv, separator=UNIQUE_SEPARATOR)

    def validate(self):
        """Validate this pipe."""
        self.source_class_name = self.merged_dict.get(self.Key.SOURCE.value, {}).get(self.Key.CLASS.value, "")
        if not self.source_class_name:
            raise RuntimeError("No source class name defined on this pipe")

        self.target_class_name = self.merged_dict.get(self.Key.TARGET.value, {}).get(self.Key.CLASS.value, "")
        if not self.target_class_name:
            raise RuntimeError("No target class name defined on this pipe")

    def run(self):
        """Run this pipe."""
        self.validate()
        source_class = BaseSource.get_class_from(self.source_class_name)
        target_class = BaseTarget.get_class_from(self.target_class_name)
        click.secho(
            f"Pipe: {self.name} ({pretty_plugin_name(source_class)} -> {pretty_plugin_name(target_class)})",
            fg="bright_green",
        )

        source_dict: JsonDict = self.merged_dict.get(self.Key.SOURCE.value).copy()
        LOGGER.debug("source_dict: %s", source_dict)
        source_dict.pop(self.Key.CLASS.value)
        source_template = json.dumps(source_dict)
        expanded_source_dict = json.loads(Template(source_template, undefined=StrictUndefined).render(env=os.environ))
        LOGGER.debug("expanded_source_dict: %s", expanded_source_dict)

        target_dict: JsonDict = self.merged_dict.get(self.Key.TARGET.value).copy()
        target_dict.pop(self.Key.CLASS.value)
        target_template = json.dumps(target_dict)

        has_items = False
        source_instance = source_class()
        for item_dict in source_instance.pull(expanded_source_dict):
            LOGGER.debug("item_dict: %s", item_dict)
            LOGGER.debug("target_template: %s", target_template)

            rendered_item = Template(target_template).render({"env": os.environ, source_class.name: item_dict})
            LOGGER.debug("rendered_item: %s", rendered_item)
            expanded_item_dict = json.loads(rendered_item)
            LOGGER.debug("expanded_item_dict: %s", expanded_item_dict)
            click.echo("  Pushing ", nl=False)
            target = target_class()
            success = target.push(expanded_item_dict)
            if success:
                click.secho("ok", fg="green")
                source_instance.on_success()
            else:
                click.secho(f"not saved: {target.validation_error}", fg="yellow")
                source_instance.on_failure()
            has_items = True

        if not has_items:
            click.echo("  No items on source")


class PipeType(Enum):
    """Types of pipes."""

    ALL = "all"
    DEFAULT = "default"
    USER = "user"


class PipeConfig(SingletonMixin):
    """Pipe configuration."""

    @memoized_property
    def default_pipes(self) -> Set[Pipe]:
        """Default pipes."""
        return self._find_pipes_in([Path(__file__).parent / DEFAULT_PIPES_DIR_NAME])

    @memoized_property
    def user_pipes(self) -> Set[Pipe]:
        """Default pipes."""
        return self._find_pipes_in(USER_PIPES_DIR)

    @memoized_property
    def pipes_by_name(self) -> Dict[str, Pipe]:
        """A dict of pipes with the (case insensitive) pipe name as key."""
        return {pipe.name.casefold(): pipe for pipe in itertools.chain(self.default_pipes, self.user_pipes)}

    @memoized_property
    def sources(self) -> Dict[str, Type["BaseSource"]]:
        """Configured sources."""
        return {source_class.name: source_class for source_class in get_subclasses(BaseSource)}

    @memoized_property
    def targets(self) -> Dict[str, Type["BaseTarget"]]:
        """Configured targets."""
        return {target_class.name: target_class for target_class in get_subclasses(BaseTarget)}

    @staticmethod
    def _find_pipes_in(directories: List[Union[str, Path]]) -> Set[Pipe]:
        """Find pipe files in the provided list of directories."""
        valid_dirs = []
        invalid_dirs = []
        for my_pipe_dir in directories:
            path = Path(my_pipe_dir).expanduser().resolve()
            if not path.exists():
                invalid_dirs.append(path)
            else:
                valid_dirs.append(path)

        if invalid_dirs:
            invalid_dirs_str = [str(path) for path in invalid_dirs]
            raise RuntimeError(f"Invalid directories in MY_PIPES_DIRS: {', '.join(invalid_dirs_str)}")

        unique_toml_files = set()
        for valid_dir in valid_dirs:
            unique_toml_files.update(list(valid_dir.glob("*.toml")))

        return {Pipe(toml_file) for toml_file in unique_toml_files}

    def echo(self, header: str, default: bool) -> "PipeConfig":
        """Echo default or user pipes to the terminal."""
        click.secho(f"{header}:", fg="bright_yellow")
        for pipe in self.default_pipes if default else self.user_pipes:
            pipe.echo()
        return self

    def get_pipe(self, exact_name: str) -> Optional[Pipe]:
        """Get a pipe by its exact name (case insensitive comparison)."""
        return self.pipes_by_name.get(exact_name.casefold(), None)

    def get_pipes(self, partial_name: str) -> List[Pipe]:
        """Get pipes by its partial name (case insensitive comparison)."""
        return find_partial_keys(self.pipes_by_name, partial_name, not_found="There are no pipes named {!r}")


PIPE_CONFIG = PipeConfig.singleton()


class BaseSource(metaclass=abc.ABCMeta):
    """Base source."""

    @classproperty
    def name(cls) -> str:
        """Name of this source class."""
        return cls.__name__.replace("Source", "").casefold()  # type: ignore

    @classmethod
    def get_class_from(cls, class_name: str) -> Type["BaseSource"]:
        """Get a source class by its case insensitive name."""
        found = find_partial_keys(
            PIPE_CONFIG.sources,
            class_name,
            not_found="There is no source named {!r}",
            multiple="There are multiple sources named {!r}",
        )
        return found[0]

    @abc.abstractmethod
    def pull(self, connection_info: JsonDict) -> Iterator[JsonDict]:
        """Pull items from the source, using the provided connection info."""

    def on_success(self):
        """Hook to do something when an item was pushed successfully."""

    def on_failure(self):
        """Hook to do something when an item failed when pushed."""


class BaseTarget(metaclass=abc.ABCMeta):
    """Base target."""

    def __init__(self):
        # Loaded and validated data, in Python format (e.g. dates are like ``datetime(2019, 4, 6)``).
        self.valid_data: JsonDict = {}

        # Serialised data (e.g. dates are converted from Python to string).
        self.serialised_data: JsonDict = {}

        self.validation_error: Optional[str] = None

    @classproperty
    def name(cls) -> str:
        """Name of this target class."""
        return cls.__name__.replace("Target", "").casefold()  # type: ignore

    @classmethod
    def get_class_from(cls, class_name: str) -> Type["BaseTarget"]:
        """Get a target class by its case insensitive name."""
        found = find_partial_keys(
            PIPE_CONFIG.targets,
            class_name,
            not_found="There is no target named {!r}",
            multiple="There are multiple targets named {!r}",
        )
        return found[0]

    @abc.abstractmethod
    def push(self, raw_data: JsonDict) -> bool:
        """Push data to the target."""

    @property
    def unique_key(self):
        """Unique key for the data, based on the ID that was set by the caller."""
        return f"({self.valid_data['id']})"


@click.group()
def pipe():
    """Pipes that pull data from a source and push it to a target."""
    load_plugins()


@pipe.command()
@click.option("--all", "-a", "which", flag_value=PipeType.ALL, default=True, help="All pipes")
@click.option("--default", "-d", "which", flag_value=PipeType.DEFAULT, help="Default pipes")
@click.option("--user", "-u", "which", flag_value=PipeType.USER, help="User pipes")
def ls(which: PipeType):
    """List default and user pipes."""
    if which == PipeType.DEFAULT or which == PipeType.ALL:
        PIPE_CONFIG.echo("Default pipes", True)
    if which == PipeType.USER or which == PipeType.ALL:
        PIPE_CONFIG.echo("User pipes", False)


@pipe.command()
@click.argument("partial_names", nargs=-1)
def run(partial_names: Tuple[str, ...]):
    """Run the chosen pipes."""
    chosen_pipes: List[Pipe] = []
    for partial_name in partial_names:
        chosen_pipes.extend(PIPE_CONFIG.get_pipes(partial_name))
    if not chosen_pipes:
        chosen_pipes = PIPE_CONFIG.user_pipes
    for chosen_pipe in sorted(chosen_pipes):
        chosen_pipe.run()
