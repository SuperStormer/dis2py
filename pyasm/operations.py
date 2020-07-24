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

class Iter(Operation):
	def __init__(self, val):
		self.val = val
	
	def __str__(self):
		return f"iter({self.val})"

class ForLoop(Operation):
	def __init__(self, index, iterator):
		self.index = index
		self.iterator = iterator
	
	def __str__(self):
		return f"for {self.index} in {self.iterator}:"

class BinarySubscript(Operation):
	def __init__(self, subscript, val):
		self.subscript = subscript
		self.val = val
	
	def __str__(self):
		return f"{self.val}[{self.subscript}]"

_unary_operators = {"positive": "+", "negative": "-", "not": "not", "invert": "~"}

def unary_operation(operation: str):
	operator = _unary_operators[operation.lower()]
	
	class UnaryOperation(Operation):
		def __init__(self, val):
			self.val = val
		
		def __str__(self):
			return f"{operator}({self.val})"
	
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
	#subscr
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
			return f"({self.left}){operator}({self.right})"
	
	return BinaryOperation

def inplace_operation(operation: str):
	operator = _binary_operators[operation.lower()]
	
	class InplaceOperation(Operation):
		def __init__(self, left, right):
			self.left = left
			self.right = right
		
		def __str__(self):
			return f"{self.left}=(({self.left}){operator}({self.right}))"
	
	return InplaceOperation