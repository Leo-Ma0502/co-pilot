# class VariableMonitor:
#     def __init__(self, initial_value=None):
#         self._value = initial_value
#         self._callback = None

#     @property
#     def value(self):
#         return self._value

#     @value.setter
#     def value(self, new_value):
#         if new_value != self._value:
#             self._value = new_value
#             if self._callback:
#                 self._callback(new_value)

#     def set_callback(self, callback):
#         self._callback = callback
class VariableMonitor:
    def __init__(self, initial_value=None):
        self._value = initial_value
        self._callback = None

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, new_value):
        if new_value != self._value:
            previous_value = self._value
            self._value = new_value
            if self._callback:
                self._callback(new_value, previous_value)

    def set_callback(self, callback):
        self._callback = callback