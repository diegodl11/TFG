from collections import deque

class Stack:
    def __init__(self):
        self.items = deque()

    def push(self, item):
        self.items.append(item)

    def pop(self):
        if not self.is_empty():
            return self.items.pop()
        raise IndexError("Pop de una pila vacía")

    def peek(self):
        return self.items[-1] if not self.is_empty() else None

    def is_empty(self):
        return len(self.items) == 0

    def size(self):
        return len(self.items)

# Ejemplo de uso
"""
stack = Stack()
stack.push("A")
stack.push("B")
stack.push("C")

print(stack.pop())  # C
print(stack.peek())  # B
"""
