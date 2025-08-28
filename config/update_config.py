import yaml
import argparse
from pathlib import Path


WORKING_DIR_PATH = Path.cwd()
CONFIG_FILE_PATH = WORKING_DIR_PATH.joinpath("config", "config.yaml")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update configuration file.")
    parser.add_argument("--size", type=str, required=True)
    parser.add_argument("--model", type=str, required=True)
    parser.add_argument("--max_cells", type=int, required=True)
    parser.add_argument("--density_param", type=float, required=True)
    parser.add_argument("--green_param", type=float, required=True)
    parser.add_argument("--uhei_param", type=float, required=True)
    parser.add_argument("--beta_streets", type=float, required=True)
    parser.add_argument("--alpha_yards", type=float, required=True)
    parser.add_argument("--alpha_uhei", type=float, required=True)
    parser.add_argument("--res_name", type=str, required=True)

    args = parser.parse_args()

    # Load YAML file
    with open(CONFIG_FILE_PATH, "r") as config_file:
        config = yaml.safe_load(config_file)

    # Update values
    config["size"] = args.size
    config["model"] = args.model
    config["max_cells"] = args.max_cells
    config["density_param"] = args.density_param
    config["green_param"] = args.green_param
    config["uhei_param"] = args.uhei_param
    config["beta_streets"] = args.beta_streets
    config["alpha_yards"] = args.alpha_yards
    config["alpha_uhei"] = args.alpha_uhei
    config["res_name"] = args.res_name

    # Write back to file
    with open(CONFIG_FILE_PATH, "w") as config_file:
        yaml.dump(config, config_file, sort_keys=False)
