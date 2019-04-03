"""Pipes."""
import itertools
from pathlib import Path
from pprint import pprint
from typing import Dict, List, Union

import toml

from dontforget.settings import PIPE_DIRS


class BasePipe:
    """Base pipe."""

    def __init__(self):
        self.default_pipes: Dict[str, Path] = {}
        self.user_pipes: Dict[str, Path] = {}

        self.default_pipes = self.find_pipe_files([Path(__file__).parent / "pipes"])
        self.user_pipes = self.find_pipe_files(PIPE_DIRS)

    def find_pipe_files(self, directories: List[Union[str, Path]]) -> Dict[str, Path]:
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

        rv = {}
        for one_file in unique_toml_files:
            rv[one_file.name] = one_file
        return rv


if __name__ == "__main__":
    pipe = BasePipe()
    pprint(pipe.default_pipes)
    pprint(pipe.user_pipes)

    for name, pipe_file in itertools.chain(pipe.default_pipes.items(), pipe.user_pipes.items()):
        print(name)
        pprint(toml.loads(pipe_file.read_text()))
