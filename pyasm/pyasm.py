from pyasm.operations import Value
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

def get_code_obj_name(s):
	match = re.match(r"<code object <(.+)> at (0x[0-9a-f]+).*>", s)
	return match.group(1) + "_" + match.group(2)

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

def instructions_to_asts(instructions, is_comp=False):
	""" converts list of instruction into an AST"""
	temp_name = "__comp_temp"  # name of temporary list/set/etc for comprehensions
	indent = 0
	# list of all future changes in indentation (caused by loops,if,etc). format is (offset,change)
	indent_changes = []
	ast = []
	
	def push(operation):
		ast.append((indent, operation))
	
	def pop():
		return ast.pop()[1]
	
	def pop_n(n):
		nonlocal ast
		if n > 0:  # ast[:-0] would be the empty list and ast[-0:] would be every element in ast
			ret = [x for _, x in ast[-n:]]
			ast = ast[:-n]
		else:
			ret = []
		return ret
	
	def peek(i=1):
		return ast[-i][1]
	
	def dedent_jump_to(offset):
		for instruction2 in instructions:
			if instruction2.opname == "JUMP_ABSOLUTE" and instruction2.arg == offset:
				indent_changes.append((instruction2.offset + 2, -1))
				break
	
	i = 0
	while i < len(instructions):
		instruction = instructions[i]
		opname = instruction.opname
		if indent_changes:
			to_remove = []
			for indent_change in indent_changes:
				if indent_change[0] == instruction.offset:
					indent += indent_change[1]
					to_remove.append(indent_change)
			for indent_change in to_remove:
				indent_changes.remove(indent_change)
		if opname in ("LOAD_METHOD", "LOAD_ATTRIBUTE"):
			push(operations.Attribute(instruction.argval, pop()))
		elif opname.startswith("LOAD"):
			push(operations.Value(instruction.argval))
		elif opname in ("STORE_FAST", "STORE_NAME", "STORE_GLOBAL"):
			push(operations.Assign(instruction.argval, pop()))
		elif opname == "YIELD_VALUE":
			push(operations.Yield(pop()))
		elif opname == "RETURN_VALUE":
			if is_comp:
				push(operations.Return(operations.Value(temp_name)))
			else:
				push(operations.Return(pop()))
		elif opname == "BUILD_MAP":
			count = int(instruction.arg)
			args = pop_n(2 * count)
			push(operations.BuildMap(args))
		elif opname == "BUILD_SLICE":
			if instruction.arg == 2:
				stop = pop()
				start = pop()
				push(operations.Slice(start, stop))
			else:
				step = pop()
				stop = pop()
				start = pop()
				push(operations.Slice(start, stop, step))
		elif opname.startswith("BUILD"):
			operation = opname[len("BUILD_"):]
			count = int(instruction.arg)
			args = pop_n(count)
			push(operations.build_operation(operation)(args))
		elif opname == "GET_ITER":
			push(operations.Iter(pop()))
		elif opname == "FOR_ITER":
			iterator = pop().val  # top of stack is a GET_ITER, so we get the actual value
			assign_op = instructions[i + 1]  # get next instruction
			i += 1
			if assign_op.opname in ("STORE_FAST", "STORE_NAME", "STORE_GLOBAL"):
				index = assign_op.argval
				#dedent end of loop
				loop_end = int(instruction.argval[len("to "):])
				indent_changes.append((loop_end, -1))
				#print(indent_changes)
				push(operations.ForLoop(index, iterator))
				indent += 1
			else:
				push(operations.Invalid(opname, instruction.arg, instruction.argval))
		elif opname == "POP_JUMP_IF_FALSE":
			val = pop()
			jump_target = int(instruction.arg)
			if jump_target > instruction.offset:
				indent_changes.append((jump_target, -1))
			else:  # if this is the last statement in a for loop, it jumps directly to the top of the for loop, so we dedent the JUMP_ABSOLUTE again
				dedent_jump_to(jump_target)
			push(operations.If(val))
			indent += 1
		elif opname == "POP_JUMP_IF_TRUE":
			val = pop()
			jump_target = int(instruction.arg)
			if jump_target > instruction.offset:
				indent_changes.append((jump_target, -1))
			else:  # if this is the last statement in a for loop, it jumps directly to the top of the for loop, so we dedent the JUMP_ABSOLUTE again
				dedent_jump_to(jump_target)
			push(operations.If(operations.unary_operation("not")(val)))
			indent += 1
		elif opname == "JUMP_ABSOLUTE":
			jump_target = int(instruction.arg)
			for instruction2 in instructions:
				if instruction2.offset == jump_target:
					if instruction2.opname == "FOR_ITER":
						loop_end = int(instruction2.argval[len("to "):]) - 2
						if loop_end != instruction.offset:  # this isn't the end of the loop, but its still jumping, so this is a "continue"
							if not isinstance(peek(), operations.Break):
								push(operations.Continue())
					else:  # this isn't jumping to the start of a loop, so this is a "break"
						push(operations.Break())
					break
		elif opname == "JUMP_FORWARD":
			indent -= 1
			push(operations.Else())
			indent += 2
			jump_target = int(instruction.argval[len("to "):])
			indent_changes.append((jump_target, -1))
		elif opname in ("CALL_FUNCTION", "CALL_METHOD"):
			argc = int(instruction.arg)
			args = pop_n(argc)
			func = pop()
			push(operations.FunctionCall(func, args))
		elif opname == "CALL_FUNCTION_KW":
			# top of stack is a tuple of kwarg names pushed by LOAD_CONST
			kwarg_names = literal_eval(pop().val)
			kwargs = {}
			for name in kwarg_names:
				kwargs[name] = pop()
			argc = int(instruction.arg) - len(kwargs)
			args = pop_n(argc)
			func = pop()
			push(operations.FunctionCall(func, args, kwargs))
		elif opname == "MAKE_FUNCTION":  # list comps and lambdas
			pop()
			push(operations.Value(get_code_obj_name(pop().val)))
		elif opname in ("LIST_APPEND", "SET_ADD"):
			func = opname[opname.index("_") + 1:].lower()
			if is_comp:
				push(
					operations.FunctionCall(
					operations.Attribute(operations.Value(func), operations.Value(temp_name)),
					[pop()]
					)
				)
			else:
				push(operations.Invalid(opname, instruction.arg, instruction.argval))
		elif opname == "COMPARE_OP":
			right = pop()
			left = pop()
			push(operations.Comparison(instruction.argval, left, right))
		elif opname == "BINARY_SUBSCR":
			if isinstance(peek(), operations.Slice):
				slice_ = pop()
				val = pop()
				push(operations.SubscriptSlice(val, slice_.start, slice_.stop, slice_.step))
			else:
				subscript = pop()
				val = pop()
				push(operations.BinarySubscript(val, subscript))
		elif opname == "STORE_SUBSCR":
			push(operations.SubscriptAssign(pop(), pop(), pop()))
		elif opname.startswith("UNARY"):
			operation = opname[len("UNARY_"):]
			push(operations.unary_operation(operation)(pop()))
		elif opname.startswith("BINARY"):
			operation = opname[len("BINARY_"):]
			push(operations.binary_operation(operation)(pop(), pop()))
		elif opname.startswith("INPLACE"):
			operation = opname[len("INPLACE_"):]
			push(operations.inplace_operation(operation)(pop(), pop()))
		elif opname not in ("NOP", "POP_TOP"):
			push(operations.Invalid(opname, instruction.arg, instruction.argval))
		if i == 0 and is_comp:  #give the temporary for list comps a name
			push(operations.Assign(operations.Value(temp_name), pop()))
		i += 1
	return ast

def asts_to_code(asts):
	""" converts an ast into python code"""
	return "\n".join("\t" * indent + str(ast) for indent, ast in asts)

def asm(disasm):
	instructions = dis_to_instructions(disasm)
	asts = instructions_to_asts(instructions)
	return asts_to_code(asts)

def split_funcs(disasm):
	""" splits out comprehensions from the main func """
	start_positions = [0]
	end_positions = []
	names = ["main"]
	for match in re.finditer(r"Disassembly of (<.+>):", disasm):
		end_positions.append(match.start())
		start_positions.append(match.end())
		names.append(get_code_obj_name(match.group(1)))
	end_positions.append(len(disasm))
	for start, end, name in zip(start_positions, end_positions, names):
		yield (name, disasm[start:end])

def asm_all(disasm):
	for name, func in split_funcs(disasm):
		is_comp = "comp" in name
		yield asm(func)