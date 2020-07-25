from .dis2py import pretty_decompile
import sys
if __name__ == "__main__":
	with open(sys.argv[1]) as f:
		print(pretty_decompile(f.read()))
