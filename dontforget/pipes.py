"""Pipes."""
import itertools
from pathlib import Path
from pprint import pprint
from typing import Dict, List, Optional, Set, Union

import click
import toml

from dontforget.constants import DEFAULT_PIPES_DIR_NAME, KEY_PARENT_PIPES, UNIQUE_SEPARATOR
from dontforget.generic import SingletonMixin, flatten, unflatten
from dontforget.settings import USER_PIPES_DIR
from dontforget.typedefs import JsonDict


class Pipe:
    """A pipe to pull data from a source and push to a target."""

    def __init__(self, toml_file: Path):
        self.name = toml_file.stem
        self.path = toml_file.resolve()
        self.original_dict: JsonDict = toml.loads(toml_file.read_text())
        self._merged_dict: JsonDict = {}

    def echo(self):
        """Echo a pipe on the teminal."""
        click.secho(f"\n>>> {self.name} @ {self.path}", fg="bright_white")
        self.echo_dict()

    def echo_dict(self):
        """Pretty print the pipe structure as a dict."""
        pprint(self.merged_dict)

    @property
    def merged_dict(self) -> JsonDict:
        """Return the original dict merged with the parent pipes."""
        if not self._merged_dict:
            self._merged_dict = self.merge_parent_pipes()
        return self._merged_dict

    def merge_parent_pipes(self) -> JsonDict:
        """Merge parent pipes (first) into this pipe (last)."""
        original_without_pipes: JsonDict = self.original_dict.copy()
        parent_pipes: List[str] = original_without_pipes.pop(KEY_PARENT_PIPES, [])
        if not parent_pipes:
            return original_without_pipes

        pipe_config = PipeConfig.get_singleton()

        rv: JsonDict = {}
        for name in parent_pipes:
            parent_pipe = pipe_config.get_pipe_by_name(name)
            rv.update(flatten(parent_pipe.original_dict, separator=UNIQUE_SEPARATOR))

        rv.update(flatten(original_without_pipes, separator=UNIQUE_SEPARATOR))

        return unflatten(rv, separator=UNIQUE_SEPARATOR)


class PipeConfig(SingletonMixin):
    """Pipe configuration."""

    def __init__(self):
        """Load default and user pipes."""
        super().__init__()
        self.default_pipes: Set[Pipe] = set()
        self.user_pipes: Set[Pipe] = set()
        self._pipes_by_name: Dict[str, Pipe] = {}

    def load_pipes(self) -> "PipeConfig":
        """Load default and user pipes."""
        self.default_pipes = self._find_pipes_in([Path(__file__).parent / DEFAULT_PIPES_DIR_NAME])
        self.user_pipes = self._find_pipes_in(USER_PIPES_DIR)
        self._pipes_by_name: Dict[str, Pipe] = {
            pipe.name.lower(): pipe for pipe in itertools.chain(self.default_pipes, self.user_pipes)
        }
        return self

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
        click.secho(header, fg="bright_yellow")
        for pipe in self.default_pipes if default else self.user_pipes:
            pipe.echo()
        return self

    def get_pipe_by_name(self, pipe_name: str) -> Optional[Pipe]:
        """Get a pipe by its name (user lower case for comparison)."""
        return self._pipes_by_name.get(pipe_name.lower(), None)


def list_pipes():
    """List the pipes of the app."""
    PipeConfig.get_singleton().load_pipes().echo("Default pipes", True).echo("User pipes", False)
