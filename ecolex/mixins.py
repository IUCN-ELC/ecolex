

class ExportValidatorMixin(object):
    INT_PARAMS = {
        'rows': {'rows_errors': 'The row value must be a number.'},
        'start': {'start_errors': 'The start value must be a number.'},
    }

    def validate_int(self, fields, field):
        try:
            int(fields[field])
        except ValueError:
            self.errors.append(self.INT_PARAMS[field])

    def validate(self, fields):
        self.errors = []
        for field in self.INT_PARAMS:
            self.validate_int(fields, field)
