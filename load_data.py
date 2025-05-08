import re
import pandas as pd
import numpy as np

def extract_values(key, content):
    # Robust, multiline regex for VALUES("key")= ...;
    pattern = rf'VALUES\("{re.escape(key)}"\)=((?:(?:\s*"[^"]*",?)+));'
    match = re.search(pattern, content, re.MULTILINE)
    if match:
        return [v.strip('"') for v in re.findall(r'"([^"]+)"', match.group(1))]
    return None

def parse_px_to_df(filename):
    with open(filename, encoding="utf-8") as f:
        content = f.read()

    # Find STUB and HEADING variable names
    stub_match = re.search(r'STUB\s*=\s*((?:"[^"]*",?\s*)+);', content)
    heading_match = re.search(r'HEADING\s*=\s*((?:"[^"]*",?\s*)+);', content)
    if not stub_match or not heading_match:
        raise ValueError("Could not find STUB or HEADING in the PX file.")

    stub_vars = [v.strip('"') for v in re.findall(r'"([^"]+)"', stub_match.group(1))]
    heading_vars = [v.strip('"') for v in re.findall(r'"([^"]+)"', heading_match.group(1))]

    # Get all possible values for each variable
    all_vars = stub_vars + heading_vars
    all_values = []
    for var in all_vars:
        values = extract_values(var, content)
        if not values:
            raise ValueError(f"Could not find values for variable '{var}' in the PX file.")
        all_values.append(values)

    # Extract DATA block
    data_match = re.search(r'DATA=\s*([\s\S]+?);', content)
    if not data_match:
        raise ValueError("Could not find DATA block in the PX file.")
    data_raw = data_match.group(1)
    data_flat = re.split(r'\s+', data_raw.replace('\n', ' ').replace('\r', ' ').strip())
    data_flat = [d for d in data_flat if d]

    def parse_value(d):
        d = d.strip('"')
        if d in ('..', '.'):
            return np.nan
        return int(d)

    data_flat = [parse_value(d) for d in data_flat]

    # Build a MultiIndex for all combinations of STUB and HEADING values
    import itertools
    index_tuples = list(itertools.product(*[all_values[i] for i in range(len(stub_vars))]))
    column_tuples = list(itertools.product(*[all_values[i+len(stub_vars)] for i in range(len(heading_vars))]))

    # Reshape data to (len(index_tuples), len(column_tuples))
    data_array = np.array(data_flat).reshape(len(index_tuples), len(column_tuples))

    # Build MultiIndex DataFrame
    index = pd.MultiIndex.from_tuples(index_tuples, names=stub_vars) if len(stub_vars) > 1 else pd.Index([t[0] for t in index_tuples], name=stub_vars[0])
    columns = pd.MultiIndex.from_tuples(column_tuples, names=heading_vars) if len(heading_vars) > 1 else pd.Index([t[0] for t in column_tuples], name=heading_vars[0])
    df = pd.DataFrame(data_array, index=index, columns=columns)
    return df

if __name__ == "__main__":
    df = parse_px_to_df("response.txt")
    print(df.head())
    # Save to CSV if you want:
    # df.to_csv("px_data.csv")
