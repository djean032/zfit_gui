# takes in dictionary of parameters and writes them to a toml file
import toml


# Create toml file and call write function
def create_toml_file(config):
    filename = f"zfit_config.toml"
    write_toml_config(config, filename)


# write toml file, take in dictionary of parameters and write to toml file created
def write_toml_config(config, filename):
    """
    Write a configuration dictionary to a TOML file.
    Args:
        config (dict): Configuration dictionary to write
        filename (str): Path to the output TOML file
    """
    try:
        with open(filename, "w") as toml_file:
            toml.dump(config, toml_file)
        print(f"Configuration successfully written to {filename}")
    except Exception as e:
        print(f"An error occurred while writing to TOML file: {e}")


# Example usage
if __name__ == "__main__":
    config = {"test": 1}
    create_toml_file(config)
