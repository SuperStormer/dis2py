from dis2py import *
import dis
from pprint import pprint
from io import StringIO

def test(i=10):
	if i == 2 or i == 4 or i == 6:
		return 1

out = StringIO()
dis.dis(test, file=out)
disasm = out.getvalue()
#print(pretty_decompile(disasm, tab_char=" " * 4))

for name, func in split_funcs(disasm):
	print(name)
	instructions = dis_to_instructions(func)
	pprint(instructions)
	asts, arg_names = instructions_to_asts(instructions, get_flags(name))
	pprint(asts)
	print(asts_to_code(asts, tab_char=" " * 4))
