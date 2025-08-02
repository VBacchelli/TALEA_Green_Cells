import yaml
import argparse
from pathlib import Path

WORKING_DIR_PATH = Path.cwd()
CONFIG_FILE_PATH = WORKING_DIR_PATH.joinpath("config", "config.yaml")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update configuration file.")
    parser.add_argument("--size", type=str, required=True)
    parser.add_argument("--max_cells", type=int, required=True)
    parser.add_argument("--density_param", type=float, required=True)
    parser.add_argument("--green_param", type=float, required=True)
    parser.add_argument("--streets_param", type=float, required=True)
    parser.add_argument("--yard_param", type=float, required=True)

    args = parser.parse_args()

    # Load YAML file
    with open(CONFIG_FILE_PATH, "r") as config_file:
        config = yaml.safe_load(config_file)

    # Update values
    config["size"] = args.size
    config["max_cells"] = args.max_cells
    config["density_param"] = args.density_param
    config["green_param"] = args.green_param
    config["streets_param"] = args.streets_param
    config["yard_param"] = args.yard_param

    # Write back to file
    with open(CONFIG_FILE_PATH, "w") as config_file:
        yaml.dump(config, config_file, sort_keys=False)
