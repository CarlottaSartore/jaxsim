from __future__ import annotations

import dataclasses
from collections.abc import Callable
from typing import Any

import jax
import jax.numpy as jnp
import jax_dataclasses
import optax

import jaxsim.api as js
import jaxsim.rbda.contacts
import jaxsim.typing as jtp
from jaxsim import logging
from jaxsim.api.common import ModelDataWithVelocityRepresentation, VelRepr
from jaxsim.terrain.terrain import FlatTerrain, Terrain

from . import common

try:
    from typing import Self
except ImportError:
    from typing_extensions import Self


@jax_dataclasses.pytree_dataclass
class RelaxedRigidContactsParams(common.ContactsParams):
    """Parameters of the relaxed rigid contacts model."""

    # Time constant
    time_constant: jtp.Float = dataclasses.field(
        default_factory=lambda: jnp.array(0.01, dtype=float)
    )

    # Adimensional damping coefficient
    damping_coefficient: jtp.Float = dataclasses.field(
        default_factory=lambda: jnp.array(1.0, dtype=float)
    )

    # Minimum impedance
    d_min: jtp.Float = dataclasses.field(
        default_factory=lambda: jnp.array(0.9, dtype=float)
    )

    # Maximum impedance
    d_max: jtp.Float = dataclasses.field(
        default_factory=lambda: jnp.array(0.95, dtype=float)
    )

    # Width
    width: jtp.Float = dataclasses.field(
        default_factory=lambda: jnp.array(0.0001, dtype=float)
    )

    # Midpoint
    midpoint: jtp.Float = dataclasses.field(
        default_factory=lambda: jnp.array(0.1, dtype=float)
    )

    # Power exponent
    power: jtp.Float = dataclasses.field(
        default_factory=lambda: jnp.array(1.0, dtype=float)
    )

    # Stiffness
    stiffness: jtp.Float = dataclasses.field(
        default_factory=lambda: jnp.array(0.0, dtype=float)
    )

    # Damping
    damping: jtp.Float = dataclasses.field(
        default_factory=lambda: jnp.array(0.0, dtype=float)
    )

    # Friction coefficient
    mu: jtp.Float = dataclasses.field(
        default_factory=lambda: jnp.array(0.5, dtype=float)
    )

    def __hash__(self) -> int:
        from jaxsim.utils.wrappers import HashedNumpyArray

        return hash(
            (
                HashedNumpyArray(self.time_constant),
                HashedNumpyArray(self.damping_coefficient),
                HashedNumpyArray(self.d_min),
                HashedNumpyArray(self.d_max),
                HashedNumpyArray(self.width),
                HashedNumpyArray(self.midpoint),
                HashedNumpyArray(self.power),
                HashedNumpyArray(self.stiffness),
                HashedNumpyArray(self.damping),
                HashedNumpyArray(self.mu),
            )
        )

    def __eq__(self, other: RelaxedRigidContactsParams) -> bool:
        return hash(self) == hash(other)

    @classmethod
    def build(
        cls: type[Self],
        *,
        time_constant: jtp.FloatLike | None = None,
        damping_coefficient: jtp.FloatLike | None = None,
        d_min: jtp.FloatLike | None = None,
        d_max: jtp.FloatLike | None = None,
        width: jtp.FloatLike | None = None,
        midpoint: jtp.FloatLike | None = None,
        power: jtp.FloatLike | None = None,
        stiffness: jtp.FloatLike | None = None,
        damping: jtp.FloatLike | None = None,
        mu: jtp.FloatLike | None = None,
    ) -> Self:
        """Create a `RelaxedRigidContactsParams` instance"""

        def default(name: str):
            return cls.__dataclass_fields__[name].default_factory()

        return cls(
            time_constant=jnp.array(
                (
                    time_constant
                    if time_constant is not None
                    else default("time_constant")
                ),
                dtype=float,
            ),
            damping_coefficient=jnp.array(
                (
                    damping_coefficient
                    if damping_coefficient is not None
                    else default("damping_coefficient")
                ),
                dtype=float,
            ),
            d_min=jnp.array(
                d_min if d_min is not None else default("d_min"), dtype=float
            ),
            d_max=jnp.array(
                d_max if d_max is not None else default("d_max"), dtype=float
            ),
            width=jnp.array(
                width if width is not None else default("width"), dtype=float
            ),
            midpoint=jnp.array(
                midpoint if midpoint is not None else default("midpoint"), dtype=float
            ),
            power=jnp.array(
                power if power is not None else default("power"), dtype=float
            ),
            stiffness=jnp.array(
                stiffness if stiffness is not None else default("stiffness"),
                dtype=float,
            ),
            damping=jnp.array(
                damping if damping is not None else default("damping"), dtype=float
            ),
            mu=jnp.array(mu if mu is not None else default("mu"), dtype=float),
        )

    def valid(self) -> jtp.BoolLike:

        return bool(
            jnp.all(self.time_constant >= 0.0)
            and jnp.all(self.damping_coefficient > 0.0)
            and jnp.all(self.d_min >= 0.0)
            and jnp.all(self.d_max <= 1.0)
            and jnp.all(self.d_min <= self.d_max)
            and jnp.all(self.width >= 0.0)
            and jnp.all(self.midpoint >= 0.0)
            and jnp.all(self.power >= 0.0)
            and jnp.all(self.mu >= 0.0)
        )


@jax_dataclasses.pytree_dataclass
class RelaxedRigidContacts(common.ContactModel):
    """Relaxed rigid contacts model."""

    parameters: RelaxedRigidContactsParams = dataclasses.field(
        default_factory=RelaxedRigidContactsParams.build
    )

    terrain: jax_dataclasses.Static[Terrain] = dataclasses.field(
        default_factory=FlatTerrain.build
    )

    _solver_options_keys: jax_dataclasses.Static[tuple[str, ...]] = dataclasses.field(
        default=("tol", "maxiter", "memory_size"), kw_only=True
    )
    _solver_options_values: jax_dataclasses.Static[tuple[Any, ...]] = dataclasses.field(
        default=(1e-6, 50, 10), kw_only=True
    )

    @property
    def solver_options(self) -> dict[str, Any]:

        return dict(
            zip(
                self._solver_options_keys,
                self._solver_options_values,
                strict=True,
            )
        )

    @classmethod
    def build(
        cls: type[Self],
        parameters: RelaxedRigidContactsParams | None = None,
        terrain: Terrain | None = None,
        solver_options: dict[str, Any] | None = None,
        **kwargs,
    ) -> Self:
        """
        Create a `RelaxedRigidContacts` instance with specified parameters.

        Args:
            parameters: The parameters of the rigid contacts model.
            terrain: The considered terrain.
            solver_options: The options to pass to the L-BFGS solver.

        Returns:
            The `RelaxedRigidContacts` instance.
        """

        if len(kwargs) != 0:
            logging.debug(msg=f"Ignoring extra arguments: {kwargs}")

        # Get the default solver options.
        default_solver_options = dict(
            zip(cls._solver_options_keys, cls._solver_options_values, strict=True)
        )

        # Create the solver options to set by combining the default solver options
        # with the user-provided solver options.
        solver_options = default_solver_options | (
            solver_options if solver_options is not None else {}
        )

        # Make sure that the solver options are hashable.
        # We need to check this because the solver options are static.
        try:
            hash(tuple(solver_options.values()))
        except TypeError as exc:
            raise ValueError(
                "The values of the solver options must be hashable."
            ) from exc

        return cls(
            parameters=(
                parameters
                if parameters is not None
                else cls.__dataclass_fields__["parameters"].default_factory()
            ),
            terrain=(
                terrain
                if terrain is not None
                else cls.__dataclass_fields__["terrain"].default_factory()
            ),
            _solver_options_keys=tuple(solver_options.keys()),
            _solver_options_values=tuple(solver_options.values()),
        )

    @jax.jit
    def compute_contact_forces(
        self,
        model: js.model.JaxSimModel,
        data: js.data.JaxSimModelData,
        *,
        link_forces: jtp.MatrixLike | None = None,
        joint_force_references: jtp.VectorLike | None = None,
    ) -> tuple[jtp.Matrix, dict[str, jtp.PyTree]]:
        """
        Compute the contact forces.

        Args:
            model: The model to consider.
            data: The data of the considered model.
            link_forces:
                Optional `(n_links, 6)` matrix of external forces acting on the links,
                expressed in the same representation of data.
            joint_force_references:
                Optional `(n_joints,)` vector of joint forces.

        Returns:
            A tuple containing as first element the computed contact forces.
        """

        # Initialize the model and data this contact model is operating on.
        # This will raise an exception if either the contact model or the
        # contact parameters are not compatible.
        model, data = self.initialize_model_and_data(model=model, data=data)
        assert isinstance(data.contacts_params, RelaxedRigidContactsParams)

        link_forces = jnp.atleast_2d(
            jnp.array(link_forces, dtype=float).squeeze()
            if link_forces is not None
            else jnp.zeros((model.number_of_links(), 6))
        )

        joint_force_references = jnp.atleast_1d(
            jnp.array(joint_force_references, dtype=float).squeeze()
            if joint_force_references is not None
            else jnp.zeros(model.number_of_joints())
        )

        references = js.references.JaxSimModelReferences.build(
            model=model,
            data=data,
            velocity_representation=data.velocity_representation,
            link_forces=link_forces,
            joint_force_references=joint_force_references,
        )

        # Compute the position and linear velocities (mixed representation) of
        # all collidable points belonging to the robot.
        position, velocity = js.contact.collidable_point_kinematics(
            model=model, data=data
        )

        # Compute the penetration depth and velocity of the collidable points.
        # Note that this function considers the penetration in the normal direction.
        δ, _, n̂ = jax.vmap(common.compute_penetration_data, in_axes=(0, 0, None))(
            position, velocity, model.terrain
        )

        # Compute the position in the constraint frame.
        position_constraint = jax.vmap(lambda δ, n̂: -δ * n̂)(δ, n̂)

        # Compute the transforms of the implicit frames corresponding to the
        # collidable points.
        W_H_C = js.contact.transforms(model=model, data=data)

        with (
            references.switch_velocity_representation(VelRepr.Mixed),
            data.switch_velocity_representation(VelRepr.Mixed),
        ):

            BW_ν = data.generalized_velocity()

            BW_ν̇_free = jnp.hstack(
                js.ode.system_acceleration(
                    model=model,
                    data=data,
                    link_forces=references.link_forces(model=model, data=data),
                    joint_force_references=references.joint_force_references(
                        model=model
                    ),
                )
            )

            M = js.model.free_floating_mass_matrix(model=model, data=data)

            Jl_WC = jnp.vstack(
                jax.vmap(lambda J, δ: J * (δ > 0))(
                    js.contact.jacobian(model=model, data=data)[:, :3, :], δ
                )
            )

            J̇_WC = jnp.vstack(
                jax.vmap(lambda J̇, δ: J̇ * (δ > 0))(
                    js.contact.jacobian_derivative(model=model, data=data)[:, :3], δ
                ),
            )

        # Compute the regularization terms.
        a_ref, R, *_ = self._regularizers(
            model=model,
            position_constraint=position_constraint,
            velocity_constraint=velocity,
            parameters=data.contacts_params,
        )

        # Compute the Delassus matrix and the free mixed linear acceleration of
        # the collidable points.
        G = Jl_WC @ jnp.linalg.pinv(M) @ Jl_WC.T
        CW_al_free_WC = Jl_WC @ BW_ν̇_free + J̇_WC @ BW_ν

        # Calculate quantities for the linear optimization problem.
        A = G + R
        b = CW_al_free_WC - a_ref

        # Create the objective function to minimize as a lambda computing the cost
        # from the optimized variables x.
        objective = lambda x, A, b: jnp.sum(jnp.square(A @ x + b))

        # ========================================
        # Helper function to run the L-BFGS solver
        # ========================================

        def run_optimization(
            init_params: jtp.Vector,
            fun: Callable,
            opt: optax.GradientTransformationExtraArgs,
            maxiter: int,
            tol: float,
        ) -> tuple[jtp.Vector, optax.OptState]:

            # Get the function to compute the loss and the gradient w.r.t. its inputs.
            value_and_grad_fn = optax.value_and_grad_from_state(fun)

            # Initialize the carry of the following loop.
            OptimizationCarry = tuple[jtp.Vector, optax.OptState]
            init_carry: OptimizationCarry = (init_params, opt.init(params=init_params))

            def step(carry: OptimizationCarry) -> OptimizationCarry:

                params, state = carry

                value, grad = value_and_grad_fn(
                    params,
                    state=state,
                    A=A,
                    b=b,
                )

                updates, state = opt.update(
                    updates=grad,
                    state=state,
                    params=params,
                    value=value,
                    grad=grad,
                    value_fn=fun,
                    A=A,
                    b=b,
                )

                params = optax.apply_updates(params, updates)

                return params, state

            # TODO: maybe fix the number of iterations and switch to scan?
            def continuing_criterion(carry: OptimizationCarry) -> jtp.Bool:

                _, state = carry

                iter_num = optax.tree_utils.tree_get(state, "count")
                grad = optax.tree_utils.tree_get(state, "grad")
                err = optax.tree_utils.tree_l2_norm(grad)

                return (iter_num == 0) | ((iter_num < maxiter) & (err >= tol))

            final_params, final_state = jax.lax.while_loop(
                continuing_criterion, step, init_carry
            )

            return final_params, final_state

        # ======================================
        # Compute the contact forces with L-BFGS
        # ======================================

        # Initialize the optimized forces with a linear Hunt/Crossley model.
        init_params = jax.vmap(
            lambda p, v: jaxsim.rbda.contacts.SoftContacts.hunt_crossley_contact_model(
                position=p,
                velocity=v,
                terrain=model.terrain,
                K=1e6,
                D=2e3,
                p=0.0,
                q=0.0,
                # No tangential initial forces.
                mu=0.0,
                tangential_deformation=jnp.zeros(3),
            )[0]
        )(position, velocity).flatten()

        # Get the solver options.
        solver_options = self.solver_options

        # Extract the options corresponding to the convergence criteria.
        # All the remaining options are passed to the solver.
        tol = solver_options.pop("tol")
        maxiter = solver_options.pop("maxiter")

        # Compute the 3D linear force in C[W] frame.
        solution, _ = run_optimization(
            init_params=init_params,
            fun=objective,
            opt=optax.lbfgs(**solver_options),
            tol=tol,
            maxiter=maxiter,
        )

        # Reshape the optimized solution to be a matrix of 3D contact forces.
        CW_fl_C = solution.reshape(-1, 3)

        # Convert the contact forces from mixed to inertial-fixed representation.
        W_f_C = jax.vmap(
            lambda CW_fl_C, W_H_C: (
                ModelDataWithVelocityRepresentation.other_representation_to_inertial(
                    array=jnp.zeros(6).at[0:3].set(CW_fl_C),
                    transform=W_H_C,
                    other_representation=VelRepr.Mixed,
                    is_force=True,
                )
            ),
        )(CW_fl_C, W_H_C)

        return W_f_C, {}

    @staticmethod
    def _regularizers(
        model: js.model.JaxSimModel,
        position_constraint: jtp.Vector,
        velocity_constraint: jtp.Vector,
        parameters: RelaxedRigidContactsParams,
    ) -> tuple:
        """
        Compute the contact jacobian and the reference acceleration.

        Args:
            model: The jaxsim model.
            penetration: The point position in the constraint frame.
            velocity: The point velocity in the constraint frame.
            parameters: The parameters of the relaxed rigid contacts model.

        Returns:
            A tuple containing the reference acceleration, the regularization matrix,
            the stiffness, and the damping.
        """

        # Extract the parameters of the contact model.
        Ω, ζ, ξ_min, ξ_max, width, mid, p, K, D, μ = (
            getattr(parameters, field)
            for field in (
                "time_constant",
                "damping_coefficient",
                "d_min",
                "d_max",
                "width",
                "midpoint",
                "power",
                "stiffness",
                "damping",
                "mu",
            )
        )

        # Get the indices of the enabled collidable points.
        indices_of_enabled_collidable_points = (
            model.kin_dyn_parameters.contact_parameters.indices_of_enabled_collidable_points
        )

        parent_link_idx_of_enabled_collidable_points = jnp.array(
            model.kin_dyn_parameters.contact_parameters.body, dtype=int
        )[indices_of_enabled_collidable_points]

        # Compute the 6D inertia matrices of all links.
        M_L = js.model.link_spatial_inertia_matrices(model=model)

        def imp_aref(
            pos: jtp.Vector,
            vel: jtp.Vector,
        ) -> tuple[jtp.Vector, jtp.Vector, jtp.Vector, jtp.Vector]:
            """
            Calculates impedance and offset acceleration in constraint frame.

            Args:
                pos: position in constraint frame.
                vel: velocity in constraint frame.

            Returns:
                ξ: computed impedance
                a_ref: offset acceleration in constraint frame
                K: computed stiffness
                D: computed damping
            """

            imp_x = jnp.abs(pos) / width

            imp_a = (1.0 / jnp.power(mid, p - 1)) * jnp.power(imp_x, p)
            imp_b = 1 - (1.0 / jnp.power(1 - mid, p - 1)) * jnp.power(1 - imp_x, p)
            imp_y = jnp.where(imp_x < mid, imp_a, imp_b)

            # Compute the impedance.
            ξ = ξ_min + imp_y * (ξ_max - ξ_min)
            ξ = jnp.clip(ξ, ξ_min, ξ_max)
            ξ = jnp.where(imp_x > 1.0, ξ_max, ξ)

            # Compute the spring and damper parameters during runtime from the
            # impedance and other contact parameters.
            K = 1 / (ξ_max * Ω * ζ) ** 2
            D = 2 / (ξ_max * Ω)

            # If the user specifies K and D and they are negative, the computed `a_ref`
            # becomes something more similar to a classic Baumgarte regularization.
            K = jnp.where(K < 0, -K / ξ_max**2, K)
            D = jnp.where(D < 0, -D / ξ_max, D)

            # Compute the reference acceleration.
            a_ref = -(D * vel + K * ξ * pos)

            return ξ, a_ref, K, D

        def compute_row(
            *,
            link_idx: jtp.Int,
            pos: jtp.Vector,
            vel: jtp.Vector,
        ) -> tuple[jtp.Vector, jtp.Matrix, jtp.Vector, jtp.Vector]:

            # Compute the reference acceleration.
            ξ, a_ref, K, D = imp_aref(pos=pos, vel=vel)

            # Compute the regularization term.
            R = (
                (2 * μ**2 * (1 - ξ) / (ξ + 1e-12))
                * (1 + μ**2)
                @ jnp.linalg.inv(M_L[link_idx, :3, :3])
            )

            # Return the computed values, setting them to zero in case of no contact.
            is_active = (pos.dot(pos) > 0).astype(float)
            return jax.tree.map(
                lambda x: jnp.atleast_1d(x) * is_active, (a_ref, R, K, D)
            )

        a_ref, R, K, D = jax.tree.map(
            f=jnp.concatenate,
            tree=(
                *jax.vmap(compute_row)(
                    link_idx=parent_link_idx_of_enabled_collidable_points,
                    pos=position_constraint,
                    vel=velocity_constraint,
                ),
            ),
        )

        return a_ref, jnp.diag(R), K, D
