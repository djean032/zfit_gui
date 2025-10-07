import tomli  # For Python < 3.11, use 'pip install tomli'
# import tomllib  # For Python >= 3.11 (built-in)

def read_toml_config(filename):
    """
    Read and parse the TOML configuration file.
    
    Args:
        filename (str): Path to the TOML file
        
    Returns:
        dict: Parsed configuration data
    """
    try:
        with open(filename, 'rb') as f:
            config = tomli.load(f)  # Use tomllib.load() for Python >= 3.11
        return config
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found.")
        return None
    except tomli.TOMLDecodeError as e:
        print(f"Error parsing TOML file: {e}")
        return None


def parse_value(value):
    """
    Convert string "None" to Python None, otherwise return the value.
    
    Args:
        value: The value to parse
        
    Returns:
        Parsed value (None if "None", otherwise original value)
    """
    if isinstance(value, str) and value == "None":
        return None
    return value


def process_config(config):
    """
    Process the configuration dictionary and convert "None" strings to Python None.
    
    Args:
        config (dict): Raw configuration dictionary
        
    Returns:
        dict: Processed configuration with None values converted
    """
    processed = {}
    
    for section, params in config.items():
        processed[section] = {}
        for key, value in params.items():
            processed[section][key] = parse_value(value)
    
    return processed


def display_config(config):
    """
    Display the parsed configuration in a readable format.
    
    Args:
        config (dict): Configuration dictionary to display
    """
    print("\n" + "="*50)
    print("PARSED CONFIGURATION")
    print("="*50)
    
    for section, params in config.items():
        print(f"\n[{section}]")
        for key, value in params.items():
            print(f"  {key}: {value} (type: {type(value).__name__})")


def main():
    """Main function to read, parse, and display the TOML configuration."""
    
    # Specify your TOML filename
    toml_file = "config.toml"
    
    # Read the TOML file
    print(f"Reading TOML file: {toml_file}")
    config = read_toml_config(toml_file)
    
    if config is None:
        return
    
    # Process the config to convert "None" strings to Python None
    processed_config = process_config(config)
    
    # Display the configuration
    display_config(processed_config)
    
    # Example: Access specific parameters
    print("\n" + "="*50)
    print("ACCESSING SPECIFIC PARAMETERS")
    print("="*50)
    
    # Access laser parameters
    if 'laser' in processed_config:
        laser_params = processed_config['laser']
        print(f"\nLaser wavelength: {laser_params.get('lambda_laser')}")
        print(f"Energy per pulse: {laser_params.get('energy_pulse')}")
        print(f"Beam waist (W_o): {laser_params.get('W_o')}")
    
    # Access sample parameters
    if 'sample' in processed_config:
        sample_params = processed_config['sample']
        print(f"\nSample thickness: {sample_params.get('thickness')}")
        print(f"Surface temperature: {sample_params.get('T_surf')}")
        print(f"Concentration: {sample_params.get('concentration')}")
    
    # Return the processed config for further use
    return processed_config


if __name__ == "__main__":
    config = main()