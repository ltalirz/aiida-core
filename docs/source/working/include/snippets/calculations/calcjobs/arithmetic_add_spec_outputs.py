from aiida.engine import CalcJob

class ArithmeticAddCalculation(CalcJob):
    """Implementation of CalcJob to add two numbers for tests and demonstration purposes."""

    @classmethod
    def define(cls, spec):
        super(ArithmeticAddCalculation, cls).define(spec)
        spec.input('x', valid_type=orm.Int, help='The left operand.')
        spec.input('y', valid_type=orm.Int, help='The right operand.')
        spec.output('sum', valid_type=orm.Int, help='The sum of the left and right operand.')
