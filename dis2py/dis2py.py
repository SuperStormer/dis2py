import re
from ast import literal_eval
from dataclasses import dataclass

from . import operations

COMPREHENSION = 0b1
GEN_EXPR=0b10
@dataclass
class Instruction:
	line_num: int
	offset: int
	opname: str
	arg: int
	argval: object

def get_code_obj_name(s):
	
	match = re.match(r"<code object <?(.*?)>? at (0x[0-9a-f]+).*>", s)
	return match.group(1) + "_" + match.group(2)

def dis_to_instructions(disasm):
	""" converts output of dis.dis into list of instructions"""
	line_num = None
	instructions = []
	extended_arg = None
	has_extended_arg = False
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
			if opname == "EXTENDED_ARG":
				extended_arg = arg
				has_extended_arg = True
				continue
			if has_extended_arg:
				arg |= extended_arg << 8  # set val of high byte
				has_extended_arg = False
			argval = match["argval"]
			instructions.append(Instruction(line_num, offset, opname, arg, argval))
	return instructions

def is_store(instruction):
	return instruction.opname in ("STORE_FAST", "STORE_NAME", "STORE_GLOBAL")

def is_identifier(s:str):
	return str.isidentifier(s) and s not in ("True","False","None")
def instructions_to_asts(instructions, flags=0):
	""" converts list of instruction into an AST"""
	is_comp=flags&COMPREHENSION
	is_genexpr = flags&GEN_EXPR
	temp_name = "__temp"  # name of temporary list/set/etc for comprehensions
	indent = 0
	arg_names = []
	var_names = []
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
	
	def push_invalid(instruction):
		push(operations.Invalid(instruction.opname, instruction.arg, instruction.argval))
	
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
			push(operations.Attribute(pop(), instruction.argval))
		elif opname.startswith("LOAD"):
			var_name = instruction.argval
			if var_name.startswith(".") and (is_comp or is_genexpr):
				var_name="__"+var_name[1:]
			if is_identifier(var_name):
				if opname != "LOAD_GLOBAL" and var_name not in var_names:
					arg_names.append(var_name)
				var_names.append(var_name)
			push(operations.Value(var_name))
		elif is_store(instruction):
			var_name = instruction.argval
			if is_identifier(var_name):
				var_names.append(var_name)
			push(operations.Assign(var_name, pop()))
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
			# used to create lists, sets and tuples
			operation = opname[len("BUILD_"):]
			count = int(instruction.arg)
			args = pop_n(count)
			push(operations.build_operation(operation)(args))
		elif opname == "GET_ITER":
			push(operations.Iter(pop()))
		elif opname == "FOR_ITER":
			iterator = pop()  
			if isinstance(iterator,operations.Iter):
				iterator=iterator.val
			assign_op = instructions[i + 1]  # get next instruction
			i += 1
			if is_store(assign_op):
				index = assign_op.argval
				var_names.append(index)
				#print(indent_changes)
				push(operations.ForLoop(index, iterator))
				indent += 1
				#detect end of loop
				loop_end = int(instruction.argval[len("to "):])
				indent_changes.append((loop_end, -1))
			elif assign_op.opname == "UNPACK_SEQUENCE":
				# loops like for i,j in zip(x,y)
				num_vals = assign_op.arg
				assign_ops = instructions[i + 1:i + num_vals + 1]
				i += num_vals  #skip all stores
				indicies = []
				for op in assign_ops:
					var_name=op.argval
					var_names.append(var_name)
					indicies.append(var_name)
				push(
					operations.ForLoop(
					operations.build_operation("tuple")(indicies), iterator
					)
				)
				indent += 1
				#detect end of loop
				loop_end = int(instruction.argval[len("to "):])
				indent_changes.append((loop_end, -1))
			else:
				push_invalid(instruction)
		elif opname.startswith("POP_JUMP"): # if statements and while loops
			val = pop()
			if opname.endswith("TRUE"):
				val=operations.unary_operation("not")(val)
			jump_target = int(instruction.arg)
			if jump_target > instruction.offset:
				indent_changes.append((jump_target, -1))
				for instruction2 in instructions:
					if instruction2.offset==jump_target-2 and instruction2.opname =="JUMP_ABSOLUTE" and instruction2.arg<instruction.offset:
						#instruction before jump target jumps above us; this is a while loop
						push(operations.WhileLoop(val))
						break
				else: # this is a normal if	
					push(operations.If(val))
			else:  
				# this is a if statement that is the last statement in a for loop, 
				# so it jumps directly to the top of the for loop, so we dedent the JUMP_ABSOLUTE again
				dedent_jump_to(jump_target)
				push(operations.If(val))
			indent += 1
		elif opname == "JUMP_ABSOLUTE":
			# used for many things, including continue, break, and jumping to the top of a loop
			jump_target = int(instruction.arg)
			for instruction2 in instructions:
				if instruction2.offset == jump_target:
					if instruction2.opname == "FOR_ITER":
						loop_end = int(instruction2.argval[len("to "):]) - 2
						if loop_end != instruction.offset:  # this isn't the end of the loop, but its still jumping, so this is a "continue"
							if not isinstance(peek(), operations.Break):
								push(operations.Continue())
						#otherwise this is a normal jump to the top of the loop, so do nothing		
					else:
						for instruction3 in instructions:
							if instruction3.opname == "FOR_ITER" and int(instruction3.argval[len("to "):])==instruction2.offset:
								#there is a for loop also jumping to the same spot, so this is a "break"
								push(operations.Break())
								break
					break
		elif opname == "JUMP_FORWARD":
			# used to jump over the else statement from the if statement's branch
			indent -= 1
			push(operations.Else())
			indent += 2
			jump_target = int(instruction.argval[len("to "):])
			indent_changes.append((jump_target, -1))
		elif opname == "IMPORT_NAME":
			fromlist=pop()
			level=int(pop().val)
			if level==0: #absolute import
				next_op = instructions[i+1]
				if is_store(next_op):
					i+=1
					alias = next_op.argval if next_op.argval!=instruction.argval else None
					push(operations.Import(instruction.argval,alias))
				elif next_op.opname == "IMPORT_FROM":
					names = []
					i+=1
					while next_op.opname == "IMPORT_FROM":
						i+=1
						assign_op=instructions[i]
						names.append(assign_op.argval)
						i+=1
						next_op=instructions[i]
						print(next_op)
					i-=1
					push(operations.FromImport(instruction.argval,names))
				elif next_op.opname == "IMPORT_STAR":
					i+=1
					push(operations.FromImport(instruction.argval,[operations.Value("*")]))
				else:
					push_invalid(instruction)
			else:#TODO:relative import
				push_invalid(instruction)
		elif opname == "RAISE_VARARGS":
			argc = instruction.arg
			if argc==0:
				push(operations.Raise())
			elif argc==1:
				push(operations.Raise(pop()))
			else:
				push(operations.Raise(pop(),pop()))					
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
		elif opname == "CALL_FUNCTION_EX":
			if instruction.arg & 1:  #lowest bit set
				kwargs = pop()
				args = pop()
				func = pop()
				push(
					operations.FunctionCall(
					func, [operations.UnpackSeq(args),
					operations.UnpackDict(kwargs)]
					)
				)
			else:
				args = pop()
				func = pop()
				push(operations.FunctionCall(func, [operations.UnpackSeq(args)]))
		elif opname == "MAKE_FUNCTION": # list comps, lambdas and nested functions
			pop()
			push(operations.Value(get_code_obj_name(pop().val)))
		elif opname in ("LIST_APPEND", "SET_ADD"): #used in comprehensions
			func = opname[opname.index("_") + 1:].lower()
			if is_comp:
				push(
					operations.FunctionCall(
					operations.Attribute(operations.Value(temp_name), operations.Value(func)),
					[pop()]
					)
				)
			else:
				push_invalid(instruction)
		elif opname == "MAP_ADD": #used in dict comprehensions
			if is_comp:
				key = pop()
				val = pop()
				push(operations.SubscriptAssign(key, operations.Value(temp_name), val))
			else:
				push_invalid(instruction)
		elif opname == "UNPACK_SEQUENCE":
			push(operations.UnpackSeq(pop()))
		elif opname == "UNPACK_EX": # unpacking assignment
			num_vals_before = instruction.arg & 0xff
			num_vals_after = (instruction.arg >> 8) & 0xff  #high byte
			num_vals = num_vals_before + num_vals_after
			assign_ops = []
			for j in range(num_vals_before):
				assign_ops.append(instructions[i + j + 1])
			j += 1
			assign_op = instructions[i + j + 1]
			if is_store(assign_op):  #list unpack
				num_vals += 1
				assign_op.argval = "*" + assign_op.argval
				assign_ops.append(assign_op)
			j += 1
			for j in range(j, j + num_vals_after):
				assign_ops.append(instructions[i + j + 1])
			
			i += num_vals  #skip all stores
			names = []
			for op in assign_ops:
				var_name=op.argval
				var_names.append(var_name)
				names.append(var_name)
				
			push(
				operations.Assign(
				operations.build_operation("tuple")(names), pop()
				)
			)
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
				push(operations.Subscript(val, subscript))
		elif opname == "STORE_SUBSCR":
			push(operations.SubscriptAssign(pop(), pop(), pop()))
		elif opname.startswith("UNARY"):
			operation = opname[len("UNARY_"):]
			push(operations.unary_operation(operation)(pop()))
		elif opname.startswith("BINARY"):
			operation = opname[len("BINARY_"):]
			right = pop()
			left = pop()
			push(operations.binary_operation(operation)(left, right))
		elif opname.startswith("INPLACE"):
			operation = opname[len("INPLACE_"):]
			right = pop()
			left = pop()
			if is_store(instructions[i + 1]):
				i += 1
				push(operations.inplace_operation(operation)(left, right))
			else:
				push_invalid(instruction)
		elif opname not in ("NOP", "POP_TOP"):
			push_invalid(instruction)
		if i == 0 and is_comp:  #give the temporary for list comps a name
			push(operations.Assign(operations.Value(temp_name), pop()))
		i += 1
	return (ast,arg_names)

def asts_to_code(asts,tab_char="\t"):
	""" converts an ast into python code"""
	return "\n".join(tab_char * indent + str(ast) for indent, ast in asts)

def decompile(disasm, flags=0,tab_char="\t"):
	instructions = dis_to_instructions(disasm)
	asts,arg_names = instructions_to_asts(instructions, flags)
	return asts_to_code(asts,tab_char),arg_names

def split_funcs(disasm):
	""" splits out comprehensions from the main func or functions from the module"""
	start_positions = [0]
	end_positions = []
	names = []
	if not disasm.startswith("Disassembly"):
		names.append("main")
	for match in re.finditer(r"Disassembly of (.+):", disasm):
		end_positions.append(match.start())
		start_positions.append(match.end())
		name = match.group(1)
		if name.startswith("<"):
			names.append(get_code_obj_name(name))
		else:
			names.append(name)
	end_positions.append(len(disasm))
	if disasm.startswith("Disassembly"):
		start_positions.pop(0)
		end_positions.pop(0)
	for start, end, name in zip(start_positions, end_positions, names):
		yield (name, disasm[start:end])
def get_flags(name):
	if name.startswith("genexpr"):
		return GEN_EXPR
	elif "comp" in name:
		return COMPREHENSION
	else:
		return 0
def decompile_all(disasm,tab_char="\t"):
	disasm = re.sub(r"^#.*\n?", "", disasm, re.MULTILINE).strip()  # ignore comments
	for name, func in split_funcs(disasm):
		yield name, *decompile(func, get_flags(name),tab_char)

def pretty_decompile(disasm,tab_char="\t"):
	ret = []
	for name, code,arg_names in decompile_all(disasm,tab_char):
		ret.append(f"def {name}({','.join(arg_names)}):\n" + "\n".join(tab_char + line for line in code.split("\n")))
	return "\n".join(ret)
