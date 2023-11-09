from dataclasses import dataclass
import kdl

raw = """
grid {
    row {
        column {
            day { 
                value "0, 0" 
            }
            night {
                value "0, 0, dark"
            }
        }
        column {
            day {
                value "0, 1"
            }
            night {
                value "0, 1, dark"
            }
        }
    }
    row {
        column {
            day {
                value "1, 0"
            }
            night {
                value "1, 0, dark"
            }
        }
        column {
            day {
                value "1, 1"
            }
            night {
                value "1, 1, dark"
            }
        }
    }
}
"""

def strip(x):
    if isinstance(x, (tuple, list)):
        if len(x) == 1:
            return x[0]
    return x

@dataclass
class Value:
    value: str

def node2value(node: kdl.Node, raw: kdl.ParseFragment):
    args = node.args
    kwargs = {node.name: strip(node.args) for node in node.nodes}
    return kdl.Node(node.name, args=[Value(**kwargs)])

def reduce_node(node: kdl.Node, raw: kdl.ParseFragment):
    args = node.args
    for child_node in node.nodes:
        args.append(strip(child_node.args))
    return kdl.Node(name=node.name, args=args)

config = kdl.ParseConfig()
config = kdl.ParseConfig(nodeConverters={"day":node2value, "night":node2value, "column": reduce_node, "row": reduce_node, "grid": reduce_node})
print(repr(kdl.parse(raw, config=config).get("grid")))
