import cmath

def calculate_roots(a: float, b: float, c: float) -> tuple[complex, complex]:
    """
    Calculate the roots of a quadratic equation ax^2 + bx + c = 0.

    Args:
        a (float): Coefficient of x^2
        b (float): Coefficient of x
        c (float): Constant term

    Returns:
        tuple[complex, complex]: A tuple containing the two roots of the equation
    """
    discriminant = cmath.sqrt(b**2 - 4*a*c)
    denominator = 2*a
    root1 = (-b + discriminant) / denominator
    root2 = (-b - discriminant) / denominator

    return root1, root2

# example usage
a = 1
b = 5
c = 6
roots = calculate_roots(a, b, c)
print("Roots are {0} and {1}".format(roots[0], roots[1]))
print(roots)
