import jax.numpy as jnp
import jaxlie

import jaxsim.typing as jtp

from .skew import Skew


class Rotation:

    @staticmethod
    def x(theta: jtp.Float) -> jtp.Matrix:
        """
        Generate a 3D rotation matrix around the X-axis.

        Args:
            theta (jtp.Float): Rotation angle in radians.

        Returns:
            jtp.Matrix: 3D rotation matrix.
        """

        return jaxlie.SO3.from_x_radians(theta=theta).as_matrix()

    @staticmethod
    def y(theta: jtp.Float) -> jtp.Matrix:
        """
        Generate a 3D rotation matrix around the Y-axis.

        Args:
            theta (jtp.Float): Rotation angle in radians.

        Returns:
            jtp.Matrix: 3D rotation matrix.
        """

        return jaxlie.SO3.from_y_radians(theta=theta).as_matrix()

    @staticmethod
    def z(theta: jtp.Float) -> jtp.Matrix:
        """
        Generate a 3D rotation matrix around the Z-axis.

        Args:
            theta (jtp.Float): Rotation angle in radians.

        Returns:
            jtp.Matrix: 3D rotation matrix.
        """

        return jaxlie.SO3.from_z_radians(theta=theta).as_matrix()

    @staticmethod
    def from_axis_angle(vector: jtp.Vector) -> jtp.Matrix:
        """
        Generate a 3D rotation matrix from an axis-angle representation.

        Args:
            vector: Axis-angle representation or the rotation as a 3D vector.

        Returns:
            The SO(3) rotation matrix.
        """

        vector = vector.squeeze()

        def theta_is_not_zero(axis: jtp.Vector) -> jtp.Matrix:

            v = axis
            theta = jnp.linalg.norm(v)

            s = jnp.sin(theta)
            c = jnp.cos(theta)

            c1 = 2 * jnp.sin(theta / 2.0) ** 2

            u = v / theta
            u = jnp.vstack(u.squeeze())

            R = c * jnp.eye(3) - s * Skew.wedge(u) + c1 * u @ u.T

            return R.transpose()

        # Use the double-where trick to prevent JAX problems when the
        # jax.jit and jax.grad transforms are applied.
        return jnp.where(
            jnp.linalg.norm(vector) > 0,
            theta_is_not_zero(
                axis=jnp.where(
                    jnp.linalg.norm(vector) > 0,
                    vector,
                    # The following line is a workaround to prevent division by 0.
                    # Considering the outer where, this branch is never executed.
                    jnp.ones(3),
                )
            ),
            # Return an identity rotation matrix when the input vector is zero.
            jnp.eye(3),
        )
