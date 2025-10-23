"""
Ando Barrier Physics - Parameter Hot-Reload Operator
Allows updating material and solver parameters during simulation without re-initialization.
"""

import bpy
from bpy.types import Operator

from ._core_loader import get_core_module

_BACKEND_ANDO = "ANDO"


def _active_backend(context) -> str:
    """Read active backend from add-on preferences."""

    try:
        addon = context.preferences.addons.get(__package__)
    except AttributeError:
        return _BACKEND_ANDO
    if not addon:
        return _BACKEND_ANDO
    return getattr(addon.preferences, "solver_backend", _BACKEND_ANDO)

class ANDO_OT_update_parameters(Operator):
    """Update simulation parameters without re-initializing"""
    bl_idname = "ando.update_parameters"
    bl_label = "Update Parameters"
    bl_options = {'REGISTER', 'UNDO'}
    
    def execute(self, context):
        from . import operators
        sim_state = operators._sim_state
        
        if _active_backend(context) != _BACKEND_ANDO:
            self.report({'WARNING'}, "Parameter hot-reload is only available with the Ando backend.")
            return {'CANCELLED'}

        if not sim_state['initialized']:
            self.report({'WARNING'}, "Simulation not initialized")
            return {'CANCELLED'}
        
        abc = get_core_module(reporter=self.report, context="Parameter hot-reload operator")
        if abc is None:
            return {'CANCELLED'}
        
        props = context.scene.ando_barrier
        
        # Update SimParams
        params = sim_state['params']
        params.dt = props.dt / 1000.0
        params.beta_max = props.beta_max
        params.min_newton_steps = props.min_newton_steps
        params.max_newton_steps = props.max_newton_steps
        params.pcg_tol = props.pcg_tol
        params.pcg_max_iters = props.pcg_max_iters
        params.contact_gap_max = props.contact_gap_max
        params.wall_gap = props.wall_gap
        params.enable_ccd = props.enable_ccd
        params.enable_friction = props.enable_friction
        params.friction_mu = props.friction_mu
        params.friction_epsilon = props.friction_epsilon
        params.velocity_damping = props.velocity_damping
        params.contact_restitution = props.contact_restitution
        params.enable_strain_limiting = props.enable_strain_limiting
        params.strain_limit = props.strain_limit
        params.strain_tau = props.strain_tau
        
        # Update material properties on the mesh
        mesh = sim_state['mesh']
        mat_props = props.material_properties
        mesh.material.youngs_modulus = mat_props.youngs_modulus
        mesh.material.poisson_ratio = mat_props.poisson_ratio
        mesh.material.density = mat_props.density
        mesh.material.thickness = mat_props.thickness
        
        # Re-initialize state masses with new material density
        # (This is safe as it only updates masses, not positions/velocities)
        state = sim_state['state']
        state.initialize(mesh)
        
        self.report({'INFO'}, "Parameters updated successfully")
        return {'FINISHED'}

def register():
    bpy.utils.register_class(ANDO_OT_update_parameters)

def unregister():
    bpy.utils.unregister_class(ANDO_OT_update_parameters)
