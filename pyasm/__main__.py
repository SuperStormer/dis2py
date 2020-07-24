from .pyasm import *
import dis
from io import StringIO
from pprint import pprint

def test():
	a = [2, 4]
	b = 2 * a
	b[0] = 5
	for i in range(start=b[1], stop=a[0]):
		print(i)

if __name__ == "__main__":
	out = StringIO()
	dis.dis(test, file=out)
	instructions = dis_to_instructions(out.getvalue())
	pprint(instructions)
	asts = instructions_to_asts(instructions)
	pprint(asts)
	print(asts_to_code(asts))