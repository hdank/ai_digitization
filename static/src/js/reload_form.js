/** @odoo-module **/

import { registry } from "@web/core/registry";

function reloadFormAction(env, action) {
    // Reload the current form view
    env.services.action.doAction({
        type: 'ir.actions.act_window',
        res_model: action.res_model,
        res_id: action.res_id,
        view_mode: 'form',
        target: 'current',
    }).then(() => {
        // Show notification after reload
        if (action.notification) {
            env.services.notification.add(
                action.notification.message,
                {
                    title: action.notification.title,
                    type: action.notification.type
                }
            );
        }
    });
}

registry.category("actions").add("reload_form_with_notification", reloadFormAction);
