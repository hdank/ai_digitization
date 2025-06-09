/** @odoo-module **/

import { registry } from "@web/core/registry";

// Custom action to reload form with notification
function reloadFormWithNotification(env, action) {
    // Show notification first
    if (action.params && action.params.notification) {
        const notification = action.params.notification;
        env.services.notification.add(notification.message, {
            title: notification.title,
            type: notification.type,
            sticky: notification.sticky || false,
        });
    }
    
    // Wait a moment for the notification to display, then reload
    setTimeout(() => {
        window.location.reload();
    }, 1000);
}

registry.category("actions").add("reload_form_with_notification", reloadFormWithNotification);
