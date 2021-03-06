from abc import abstractmethod, ABC

class Operation(ABC):
	@abstractmethod
	def __str__(self):
		pass

class Invalid(Operation):
	def __init__(self, opname, arg, argval):
		self.opname = opname
		self.arg = arg
		self.argval = argval
	
	def __str__(self):
		return f"<{self.opname}({self.arg},{self.argval})>"

class Value(Operation):
	def __init__(self, val):
		self.val = val
	
	def __str__(self):
		return self.val

class Assign(Operation):
	def __init__(self, left, right):
		self.left = left
		self.right = right
	
	def __str__(self):
		return f"{self.left}={self.right}"

class SubscriptAssign(Operation):
	def __init__(self, subscript, left, right):
		self.subscript = subscript
		self.left = left
		self.right = right
	
	def __str__(self):
		return f"{self.left}[{self.subscript}]={self.right}"

class Return(Operation):
	def __init__(self, val):
		self.val = val
	
	def __str__(self):
		return f"return {self.val}"

class Yield(Operation):
	def __init__(self, val):
		self.val = val
	
	def __str__(self):
		return f"yield {self.val}"

class ForLoop(Operation):
	def __init__(self, indicies, iterator):
		self.indicies = indicies
		self.iterator = iterator
	
	def __str__(self):
		return f"for {','.join(map(str,self.indicies))} in {self.iterator}:"

class WhileLoop(Operation):
	def __init__(self, val):
		self.val = val
	
	def __str__(self):
		return f"while {self.val}:"

class If(Operation):
	def __init__(self, val):
		self.val = val
	
	def __str__(self):
		return f"if {self.val}:"

class Elif(Operation):
	def __init__(self, val):
		self.val = val
	
	def __str__(self):
		return f"elif {self.val}:"

class Else(Operation):
	def __str__(self):
		return "else:"

class Break(Operation):
	def __str__(self):
		return "break"

class Continue(Operation):
	def __str__(self):
		return "continue"

class Import(Operation):
	def __init__(self, module, alias=None):
		self.module = module
		self.alias = alias
	
	def __str__(self):
		alias_str = "" if self.alias is None else f" as {self.alias}"
		return f"import {self.module}{alias_str}"

class FromImport(Operation):
	def __init__(self, module, vals):
		self.module = module
		self.vals = vals
	
	def __str__(self):
		return f"from {self.module} import {','.join(map(str,self.vals))}"

class Raise(Operation):
	def __init__(self, exception=None, cause=None):
		self.exception = exception
		self.cause = cause
	
	def __str__(self):
		exception_str = "" if self.exception is None else f" {self.exception}"
		cause_str = "" if self.cause is None else f" from {self.cause}"
		return f"raise{exception_str}{cause_str}"

class Jump(Operation):
	# for raw jumps flag
	def __init__(self, target, condition=None):
		self.target = target
		self.condition = condition
	
	def __str__(self):
		cond_str = f" if {self.condition}" if self.condition is not None else ""
		return f"jump {self.target}{cond_str}"

_build_operators = {"list": "[]", "tuple": "()", "set": "{}"}

def build_operation(operation):
	operator = _build_operators[operation.lower()]
	
	class BuildOperation(Operation):
		def __init__(self, args):
			self.args = args
		
		def __str__(self):
			return operator[0] + ",".join(map(str, self.args)) + operator[1]
	
	return BuildOperation

class BuildMap(Operation):
	def __init__(self, args):
		self.args = args
	
	def __str__(self):
		return "{" + "".join(f"{k}:{v}" for v, k in zip(self.args[::2], self.args[1::2])) + "}"

class FunctionCall(Operation):
	def __init__(self, func, args, kwargs=None):
		self.func = func
		self.args = args
		if kwargs is None:
			self.kwargs = {}
		else:
			self.kwargs = kwargs
	
	def __str__(self):
		kwargs = [f"{k}={v}" for k, v in self.kwargs.items()]
		return f"{self.func}({','.join(map(str,self.args+kwargs))})"

class Closure(Operation):
	def __init__(self, func, closure_vars):
		self.func = func
		self.closure_vars = closure_vars
	
	def __str__(self):
		arg_str = ','.join(map(str, self.closure_vars))
		return f"(lambda {arg_str},*args,**kwargs:{self.func}({arg_str},*args,**kwargs))"

class Attribute(Operation):
	def __init__(self, obj, prop):
		self.prop = prop
		self.obj = obj
	
	def __str__(self):
		return f"{self.obj}.{self.prop}"

class Iter(Operation):
	def __init__(self, val):
		self.val = val
	
	def __str__(self):
		return f"iter({self.val})"

class UnpackSeq(Operation):
	def __init__(self, val):
		self.val = val
	
	def __str__(self):
		return f"*{self.val}"

class UnpackDict(Operation):
	def __init__(self, val):
		self.val = val
	
	def __str__(self):
		return f"**{self.val}"

class Slice(Operation):
	def __init__(self, start, stop, step=None):
		self.start = start
		self.stop = stop
		self.step = step
	
	def __str__(self):
		step_str = f",{self.step}" if self.step is not None else ""
		return f"slice({self.start},{self.stop}{step_str})"

class SubscriptSlice(Operation):
	def __init__(self, val, start, stop, step=None):
		self.val = val
		self.start = start
		self.stop = stop
		self.step = step
	
	def __str__(self):
		start_str = self.start if self.start is not None else ""
		stop_str = self.stop if self.stop is not None else ""
		step_str = f":{self.step}" if self.step is not None else ""
		return f"{self.val}[{start_str}:{stop_str}{step_str}]"

class Subscript(Operation):
	def __init__(self, val, subscript):
		self.subscript = subscript
		self.val = val
	
	def __str__(self):
		return f"{self.val}[{self.subscript}]"

def binary_op_to_str(left, right, operator):
	if isinstance(
		left, (Value, Subscript, SubscriptSlice, Attribute, FunctionCall)
	):  #drop the parens
		left_str = str(left)
	else:
		left_str = f"({left})"
	if isinstance(
		right, (Value, Subscript, SubscriptSlice, Attribute, FunctionCall)
	):  #drop the parens
		right_str = str(right)
	else:
		right_str = f"({right})"
	return left_str + operator + right_str

class Comparison(Operation):
	def __init__(self, operator, left, right):
		if operator in ("not in", "in"):
			self.operator = f" {operator} "
		else:
			self.operator = operator
		self.left = left
		self.right = right
	
	def __str__(self):
		return binary_op_to_str(self.left, self.right, self.operator)

_unary_operators = {"positive": "+", "negative": "-", "not": "not", "invert": "~"}

def unary_operation(operation: str):
	operator = _unary_operators[operation.lower()]
	
	class UnaryOperation(Operation):
		def __init__(self, val):
			self.val = val
		
		def __str__(self):
			if isinstance(
				self.val, (Value, Subscript, SubscriptSlice, Attribute, FunctionCall)
			):  #drop the parens
				val_str = str(self.val)
			else:
				val_str = f"({self.val})"
			return operator + val_str
	
	return UnaryOperation

_binary_operators = {
	"power": "**",
	"multiply": "*",
	"matrix_multiply": "@",
	"floor_divide": "//",
	"true_divide": "/",
	"modulo": "%",
	"add": "+",
	"subtract": "-",
	"lshift": "<<",
	"rshift": ">>",
	"and": "&",
	"xor": "^",
	"or": "|"
}

def binary_operation(operation: str):
	operator = _binary_operators[operation.lower()]
	
	class BinaryOperation(Operation):
		def __init__(self, left, right):
			self.left = left
			self.right = right
		
		def __str__(self):
			return binary_op_to_str(self.left, self.right, operator)
	
	return BinaryOperation

def inplace_operation(operation: str):
	operator = _binary_operators[operation.lower()]
	
	class InplaceOperation(Operation):
		def __init__(self, left, right):
			self.left = left
			self.right = right
		
		def __str__(self):
			return f"{self.left}{operator}={self.right}"
	
	return InplaceOperation