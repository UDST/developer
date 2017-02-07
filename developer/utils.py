import yaml

def yaml_to_dict(yaml_str=None, str_or_buffer=None):
    """
    Load YAML from a string, file, or buffer (an object with a .read method).
    Parameters are mutually exclusive.

    Parameters
    ----------
    yaml_str : str, optional
        A string of YAML.
    str_or_buffer : str or file like, optional
        File name or buffer from which to load YAML.

    Returns
    -------
    dict
        Conversion from YAML.

    """
    if not yaml_str and not str_or_buffer:
        raise ValueError('One of yaml_str or str_or_buffer is required.')

    if yaml_str:
        d = yaml.load(yaml_str)
    elif isinstance(str_or_buffer, str):
        with open(str_or_buffer) as f:
            d = yaml.load(f)
    else:
        d = yaml.load(str_or_buffer)

    return d
