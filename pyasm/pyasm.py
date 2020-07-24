import re
import itertools
from dataclasses import dataclass
from . import operations
from ast import literal_eval

@dataclass
class Instruction:
	line_num: int
	offset: int
	opname: str
	arg: int
	argval: object

def dis_to_instructions(disasm):
	""" converts output of dis.dis into list of instructions"""
	line_num = None
	instructions = []
	for line in disasm.split("\n"):
		match = re.search(
			r"( (?P<line_num>\d+)\s+)?(?P<offset>\d+) (?P<opname>[A-Z_]+)(?:\s+(?P<arg>\d+)(?: \((?P<argval>.+)\))?)?",
			line
		)
		if match is not None:
			if match["line_num"]:
				line_num = int(match["line_num"])
			offset = int(match["offset"])
			opname = match["opname"]
			if match["arg"] is not None:
				arg = int(match["arg"])
			else:
				arg = None
			argval = match["argval"]
			instructions.append(Instruction(line_num, offset, opname, arg, argval))
	return instructions

def instructions_to_asts(instructions):
	lines = [
		(line_num, list(line))
		for line_num, line, in itertools.groupby(instructions, key=lambda x: x.line_num)
	]
	indent = 0
	# list of all future changes in indentation (caused by loops,if,etc). format is (line_num,change)
	indent_changes = []
	asts = []
	for line_num, line in lines:
		ast = []
		if indent_changes:
			for indent_change in indent_changes:
				if indent_change[0] == line_num:
					indent += indent_change[1]
					indent_changes.remove(indent_change)
					break
		while line:
			instruction = line.pop(0)
			opname = instruction.opname
			if opname.startswith("LOAD"):
				ast.append(operations.Value(instruction.argval))
			elif opname in ("STORE_FAST", "STORE_NAME", "STORE_GLOBAL"):
				ast.append(operations.Assign(instruction.argval, ast.pop()))
			elif opname == "YIELD_VALUE":
				ast.append(operations.Yield(ast.pop()))
			elif opname == "RETURN_VALUE":
				ast.append(operations.Return(ast.pop()))
			elif opname == "BUILD_MAP":
				count = int(instruction.arg)
				args = ast[-2 * count:]
				ast = ast[:-2 * count]
				ast.append(operations.BuildMap(args))
			elif opname.startswith("BUILD"):
				operation = opname[len("BUILD_"):]
				count = int(instruction.arg)
				args = ast[-count:]
				ast = ast[:-count]
				ast.append(operations.build_operation(operation)(args))
			elif opname == "GET_ITER":
				ast.append(operations.Iter(ast.pop()))
			elif opname == "FOR_ITER":
				iterator = ast.pop()
				assign_op = line.pop(0)  # get next instruction
				print(assign_op)
				if assign_op.opname in ("STORE_FAST", "STORE_NAME", "STORE_GLOBAL"):
					index = assign_op.argval
					indent_changes.append((line_num + 1, 1))
					for line_num2, line2 in lines:
						if line_num2 > line_num:
							for instruction2 in line2:
								if instruction2.opname == "JUMP_ABSOLUTE" and instruction2.arg == instruction.offset:
									indent_changes.append((line_num2 + 1, -1))
									break
							else:
								continue
							break
					print(indent_changes)
					ast.append(operations.ForLoop(index, iterator))
				else:
					ast.append(operations.Invalid(opname, instruction.arg, instruction.argval))
			elif opname == "CALL_FUNCTION":
				argc = int(instruction.arg)
				if argc > 0:  # ast[:-0] would be the empty list and ast[-0:] would be every element in ast
					args = ast[-argc:]
					ast = ast[:-argc]
				else:
					args = []
				func = ast.pop()
				ast.append(operations.FunctionCall(func, args))
			elif opname == "CALL_FUNCTION_KW":
				# top of stack is a tuple of kwarg names pushed by LOAD_CONST
				kwarg_names = literal_eval(ast.pop().val)
				kwargs = {}
				for name in kwarg_names:
					kwargs[name] = ast.pop()
				argc = int(instruction.arg) - len(kwargs)
				if argc > 0:  # ast[:-0] would be the empty list and ast[-0:] would be every element in ast
					args = ast[-argc:]
					ast = ast[:-argc]
				else:
					args = []
				func = ast.pop()
				ast.append(operations.FunctionCall(func, args, kwargs))
			elif opname == "BINARY_SUBSCR":
				ast.append(operations.BinarySubscript(ast.pop(), ast.pop()))
			elif opname == "STORE_SUBSCR":
				ast.append(operations.SubscriptAssign(ast.pop(), ast.pop(), ast.pop()))
			elif opname.startswith("UNARY"):
				operation = opname[len("UNARY_"):]
				ast.append(operations.unary_operation(operation)(ast.pop()))
			elif opname.startswith("BINARY"):
				operation = opname[len("BINARY_"):]
				ast.append(operations.binary_operation(operation)(ast.pop(), ast.pop()))
			elif opname.startswith("INPLACE"):
				operation = opname[len("INPLACE_"):]
				ast.append(operations.inplace_operation(operation)(ast.pop(), ast.pop()))
			else:
				ast.append(operations.Invalid(opname, instruction.arg, instruction.argval))
		asts.append((indent, ast))
	return asts

def asts_to_code(asts):
	return "\n".join("\t" * indent + str(ast2) for indent, ast in asts for ast2 in ast)

def asm(disasm):
	instructions = dis_to_instructions(disasm)
	asts = instructions_to_asts(instructions)
	return asts_to_code(asts)