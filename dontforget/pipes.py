"""Pipes."""
import abc
import itertools
from enum import Enum
from pathlib import Path
from pprint import pprint
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import click
import toml
from autorepr import autorepr
from marshmallow import ValidationError
from sqlalchemy.util import memoized_property

from dontforget.constants import DEFAULT_PIPES_DIR_NAME, UNIQUE_SEPARATOR
from dontforget.generic import SingletonMixin, flatten, unflatten
from dontforget.settings import USER_PIPES_DIR
from dontforget.typedefs import JsonDict


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

        pipe_config = PipeConfig.singleton()

        rv: JsonDict = {}
        for name in parent_pipes:
            parent_pipe = pipe_config.get_pipe(name)
            rv.update(flatten(parent_pipe.original_dict, separator=UNIQUE_SEPARATOR))

        rv.update(flatten(original_without_pipes, separator=UNIQUE_SEPARATOR))

        return unflatten(rv, separator=UNIQUE_SEPARATOR)

    def validate(self):
        """Validate this pipe."""
        self.source_class_name = self.merged_dict.get(self.Key.SOURCE.value, {}).get(self.Key.CLASS.value, "")
        if not self.source_class_name:
            raise RuntimeError("No source class name defined on this pipe")

    def run(self):
        """Run this pipe."""
        self.validate()
        click.secho(f"Running pipe {self.name}", fg="green")

        source_class = BaseSource.get_class_from(self.source_class_name)
        print("Source:", source_class)
        # TODO: expanded_source_data = Template('redmine' dict).render()
        # TODO: issues = RedmineSource().pull(expanded_source_data)
        # TODO: for each issue, expanded_issue_dict = Template(issue_dict).render()
        # TODO: TodoistTarget().push(expanded_issue_dict)


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
        return [pipe for key, pipe in self.pipes_by_name.items() if partial_name.casefold() in key.casefold()]


class BaseSource(metaclass=abc.ABCMeta):
    """Base source."""

    @classmethod
    def get_class_from(cls, class_name: str):
        """Get a source class by its case insensitive name."""
        return class_name  # FIXME: from here: find BaseSource child by class name


class BaseTarget(metaclass=abc.ABCMeta):
    """Base target."""

    def __init__(self, raw_data: Dict[str, Any]):
        self.raw_data = raw_data
        self.valid_data: Dict[str, Any] = {}
        self.validation_error: Optional[ValidationError] = None

    @abc.abstractmethod
    def process(self) -> bool:
        """Process the target data."""
        pass

    @property
    def unique_key(self):
        """Unique key for the data, based on the ID that was set by the caller."""
        return f"({self.valid_data['id']})"


@click.group()
def pipe():
    """Pipes that pull data from a source and push it to a target."""


@pipe.command()
@click.option("--all", "-a", "which", flag_value=PipeType.ALL, default=True, help="All pipes")
@click.option("--default", "-d", "which", flag_value=PipeType.DEFAULT, help="Default pipes")
@click.option("--user", "-u", "which", flag_value=PipeType.USER, help="User pipes")
def ls(which: PipeType):
    """List default and user pipes."""
    config = PipeConfig.singleton()
    if which == PipeType.DEFAULT or which == PipeType.ALL:
        config.echo("Default pipes", True)
    if which == PipeType.USER or which == PipeType.ALL:
        config.echo("User pipes", False)


@pipe.command()
@click.argument("partial_names", nargs=-1)
def run(partial_names: Tuple[str, ...]):
    """Run the chosen pipes."""
    config = PipeConfig.singleton()
    chosen_pipes: List[Pipe] = []
    for partial_name in partial_names:
        chosen_pipes.extend(config.get_pipes(partial_name))
    if not chosen_pipes:
        chosen_pipes = config.user_pipes

    for pipe in chosen_pipes:
        pipe.run()


if __name__ == "__main__":
    from jinja2 import Template, StrictUndefined
    import os

    variables = {"env": os.environ, "redmine": {"id": 666}}
    rv = Template("Here it goes {{ env.REDMINE_URL }} and {{ redmine.id }}", undefined=StrictUndefined).render(
        variables
    )
    print(rv)
