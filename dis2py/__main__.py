from .dis2py import pretty_decompile, RAW_JUMPS
import argparse

def main():
	parser = argparse.ArgumentParser(description="Converts dis.dis output into Python source code.")
	parser.add_argument("file", type=argparse.FileType("r"))
	parser.add_argument("-f", "--flags", type=int)
	parser.add_argument("-r", "--raw-jumps", action="store_true")
	args = parser.parse_args()
	flags = args.flags
	if args.raw_jumps:
		flags |= RAW_JUMPS
	with args.file as f:
		print(pretty_decompile(f.read()))

if __name__ == "__main__":
	main()