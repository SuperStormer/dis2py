from .pyasm import *
import dis
from io import StringIO
from pprint import pprint

def test():
	lambda: 2
	[i for i in (1, 2)]
	[i for i in (1, 2)]

if __name__ == "__main__":
	out = StringIO()
	dis.dis(dis_to_instructions, file=out)
	funcs = split_funcs(out.getvalue())
	for name, disasm in funcs:
		is_comp = "comp" in name
		instructions = dis_to_instructions(disasm)
		pprint(instructions)
		asts = instructions_to_asts(instructions, is_comp)
		pprint(asts)
		print(asts_to_code(asts))
