import random
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, TypeVar, Union

try:
    import orjson as json
except ImportError:
    import json

T = TypeVar('T')
Map = Union[list, tuple]


class BayesianNode:
    """
    Implementation of a single node in a bayesian network allowing sampling from its conditional distribution
    """

    def __init__(self, node_definition: Dict[str, Any]):
        self.node_definition = node_definition

    def get_probabilities_given_known_values(
        self, parent_values: Dict[str, Any]
    ) -> Dict[Any, float]:
        """
        Extracts unconditional probabilities of node values given the values of the parent nodes
        """
        probabilities = self.node_definition['conditionalProbabilities']
        for parent_name in self.parent_names:
            parent_value = parent_values.get(parent_name)
            if parent_value in probabilities.get('deeper', {}):
                probabilities = probabilities['deeper'][parent_value]
            else:
                probabilities = probabilities.get('skip', {})
        return probabilities

    def sample_random_value_from_possibilities(
        self, possible_values: List[str], probabilities: Dict[str, float]
    ) -> Any:
        """
        Randomly samples from the given values using the given probabilities
        """
        # Python natively supports weighted random sampling in random.choices,
        # but this method is much faster
        anchor = random.random()
        cumulative_probability = 0.0
        for possible_value in possible_values:
            cumulative_probability += probabilities[possible_value]
            if cumulative_probability > anchor:
                return possible_value
        # Default to first item
        return possible_values[0]

    def sample(self, parent_values: Dict[str, Any]) -> Any:
        """
        Randomly samples from the conditional distribution of this node given values of parents
        """
        probabilities = self.get_probabilities_given_known_values(parent_values)
        return self.sample_random_value_from_possibilities(
            list(probabilities.keys()), probabilities
        )

    def sample_according_to_restrictions(
        self,
        parent_values: Dict[str, Any],
        value_possibilities: Iterable[str],
        banned_values: List[str],
    ) -> Optional[str]:
        """
        Randomly samples from the conditional distribution of this node given restrictions on the possible values and the values of the parents.
        """
        probabilities = self.get_probabilities_given_known_values(parent_values)
        valid_values = [
            value
            for value in value_possibilities
            if value not in banned_values and value in probabilities
        ]
        if valid_values:
            return self.sample_random_value_from_possibilities(valid_values, probabilities)
        else:
            return None  # Equivalent to `false` in TypeScript

    @property
    def name(self) -> str:
        return self.node_definition['name']

    @property
    def parent_names(self) -> List[str]:
        return self.node_definition.get('parentNames', [])

    @property
    def possible_values(self) -> List[str]:
        return self.node_definition.get('possibleValues', [])


class BayesianNetwork:
    """
    Implementation of a bayesian network capable of randomly sampling from its distribution
    """

    def __init__(self, path: Path) -> None:
        network_definition = extract_json(path)
        self.nodes_in_sampling_order = [
            BayesianNode(node_def) for node_def in network_definition['nodes']
        ]
        self.nodes_by_name = {node.name: node for node in self.nodes_in_sampling_order}

    def generate_sample(self, input_values: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Randomly samples from the distribution represented by the bayesian network.
        """
        if input_values is None:
            input_values = {}
        sample = input_values.copy()
        for node in self.nodes_in_sampling_order:
            if node.name not in sample:
                sample[node.name] = node.sample(sample)
        return sample

    def generate_consistent_sample_when_possible(
        self, value_possibilities: Dict[str, Iterable[str]]
    ) -> Optional[Dict[str, Any]]:
        """
        Randomly samples values from the distribution represented by the bayesian network,
        making sure the sample is consistent with the provided restrictions on value possibilities.
        Returns None if no such sample can be generated.
        """
        return self.recursively_generate_consistent_sample_when_possible({}, value_possibilities, 0)

    def recursively_generate_consistent_sample_when_possible(
        self,
        sample_so_far: Dict[str, Any],
        value_possibilities: Dict[str, Iterable[str]],
        depth: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Recursively generates a random sample consistent with the given restrictions on possible values.
        """
        if depth == len(self.nodes_in_sampling_order):
            return sample_so_far
        node = self.nodes_in_sampling_order[depth]
        banned_values: List[str] = []
        sample_value = None
        while True:
            sample_value = node.sample_according_to_restrictions(
                sample_so_far,
                value_possibilities.get(node.name, node.possible_values),
                banned_values,
            )
            if sample_value is None:
                break
            sample_so_far[node.name] = sample_value
            next_sample = self.recursively_generate_consistent_sample_when_possible(
                sample_so_far, value_possibilities, depth + 1
            )
            if next_sample is not None:
                return next_sample
            banned_values.append(sample_value)
            del sample_so_far[node.name]
        return None


def array_intersection(a: Sequence[T], b: Sequence[T]) -> List[T]:
    """
    Performs a set "intersection" on the given (flat) arrays
    """
    set_b = set(b)
    return [x for x in a if x in set_b]


def array_zip(a: List[Tuple[T, ...]], b: List[Tuple[T, ...]]) -> List[Tuple[T, ...]]:
    """
    Combines two arrays into a single array using the set union
    Args:
        a: First array to be combined.
        b: Second array to be combined.
    Returns:
        Zipped (multi-dimensional) array.
    """
    return [tuple(set(x).union(y)) for x, y in zip(a, b)]


def undeeper(obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Removes the "deeper/skip" structures from the conditional probability table
    """
    if not isinstance(obj, dict):
        return obj
    result: Dict[str, Any] = {}
    for key, value in obj.items():
        if key == 'skip':
            continue
        if key == 'deeper':
            result.update(undeeper(value))
        else:
            result[key] = undeeper(value)
    return result


def filter_by_last_level_keys(tree: Dict[str, Any], valid_keys: Map) -> List[Tuple[str, ...]]:
    r"""
    Performs DFS on the Tree and returns values of the nodes on the paths that end with the given keys
    (stored by levels - first level is the root)
    ```
       1
      / \
     2   3
    / \ / \
    4 5 6 7
    ```
    filter_by_last_level_keys(tree, ['4', '7']) => [[1], [2,3]]
    """
    out: List[Tuple[str, ...]] = []

    def recurse(t: Dict[str, Any], vk: Union[Tuple[str, ...], List[str]], acc: List[str]) -> None:
        for key in t.keys():
            if not isinstance(t[key], dict) or t[key] is None:
                if key in vk:
                    nonlocal out
                    out = (
                        [(x,) for x in acc]
                        if len(out) == 0
                        else array_zip(out, [(x,) for x in acc])
                    )
                continue
            else:
                recurse(t[key], vk, acc + [key])

    recurse(tree, valid_keys, [])
    return out


def get_possible_values(
    network: 'BayesianNetwork', possible_values: Dict[str, Union[Tuple[str, ...], List[str]]]
) -> Dict[str, Sequence[str]]:
    """
    Given a `generative-bayesian-network` instance and a set of user constraints, returns an extended
    set of constraints **induced** by the original constraints and network structure
    """

    sets = []
    # For every pre-specified node, compute the "closure" for values of the other nodes
    for key, value in possible_values.items():
        if not isinstance(value, (list, tuple)):
            continue
        if len(value) == 0:
            raise ValueError(
                "The current constraints are too restrictive. No possible values can be found for the given constraints."
            )
        node = network.nodes_by_name[key]
        tree = undeeper(node.node_definition['conditionalProbabilities'])
        zipped_values = filter_by_last_level_keys(tree, value)
        sets.append({**dict(zip(node.parent_names, zipped_values)), key: value})

    # Compute the intersection of all the possible values for each node
    result: Dict[str, Sequence[str]] = {}
    for set_dict in sets:
        for key in set_dict.keys():
            if key in result:
                intersected_values = array_intersection(set_dict[key], result[key])
                if not intersected_values:
                    raise ValueError(
                        "The current constraints are too restrictive. No possible values can be found for the given constraints."
                    )
                result[key] = intersected_values
            else:
                result[key] = set_dict[key]

    return result


def extract_json(path: Path) -> dict:
    """
    Unzips a zip file if the path points to a zip file, otherwise directly loads a JSON file.

    Parameters:
        path: The path to the zip file or JSON file.

    Returns:
        A dictionary representing the JSON content.
    """
    if path.suffix != '.zip':
        # Directly load the JSON file
        with open(path, 'rb') as file:
            return json.loads(file.read())
    # Unzip the file and load the JSON content
    with zipfile.ZipFile(path, 'r') as zf:
        # Find the first JSON file in zip
        try:
            filename = next(file for file in zf.namelist() if file.endswith('.json'))
        except StopIteration:
            return {}  # Broken
        with zf.open(filename) as f:
            # Assuming only one JSON file is needed
            return json.loads(f.read())
