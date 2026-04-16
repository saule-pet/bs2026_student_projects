import uproot
import awkward as ak

def get_root_structure(file_path):
    """
    Returns a dictionary of all trees and their top-level keys in a ROOT file.
    Useful for quick navigation in the Streamlit UI.
    """
    try:
        with uproot.open(file_path) as file:
            # Recursively find all items that have 'arrays' (i.e. are Trees)
            all_trees = [k for k, v in file.items(recursive=True) if hasattr(v, "arrays")]
            structure = {}
            for t in all_trees:
                structure[t] = file[t].keys()
            return structure
    except Exception as e:
        return {"error": str(e)}

def get_branch_details(file_path, tree_name):
    """
    Returns detailed typing and meta info for branches in a specific tree.
    """
    try:
        with uproot.open(file_path) as file:
            tree = file[tree_name]
            details = {}
            for k in tree.keys():
                branch = tree[k]
                details[k] = {
                    "typename": branch.typename,
                    "interpretation": str(branch.interpretation)
                }
            return details
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # legacy behavior
    path = "data/00041834_00013937_1.dimuon.dst"
    print(f"Inspecting {path}...")
    struct = get_root_structure(path)
    if "error" in struct:
        print(struct["error"])
    else:
        for tree, keys in struct.items():
            print(f"\nTree: {tree}")
            for k in keys[:10]: # First 10
                print(f"  - {k}")
            if len(keys) > 10:
                print(f"  ... and {len(keys)-10} more")
