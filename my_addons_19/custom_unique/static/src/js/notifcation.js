/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class GomNotificationListener extends Component {
    static template = "custom_unique.GomNotificationListener";

    setup() {
        this.bus = useService("bus_service");
        this.notification = useService("notification");
        this.action = useService("action");

        console.log("GOM Notification Listener Loaded");

        // Subscribe to custom channel
        this.bus.subscribe("simple_notification", (payload) => {
            console.log("Received notification:", payload);
            if (!payload) return;

            let buttons = [];

            // Handle buttons
            if (payload.buttons && Array.isArray(payload.buttons)) {
                payload.buttons.forEach(btn => {
                    buttons.push({
                        name: btn.label,
                        primary: true,
                        onClick: () => {
                            if (btn.url) {
                                window.open(btn.url, "_blank");
                                return;
                            }
                            console.log("Button clicked:", btn.label);
                        },
                    });
                });
            }

            // Display notification
            this.notification.add(payload.message, {
                title: payload.title || "GOM Info",
                type: payload.type || "info",   // ⭐ DEFAULT = INFO
                sticky: payload.sticky ?? true,
                buttons,
            });
        });
    }
}

// Register once (avoid duplicates)
registry.category("systray").add("GomNotificationListener", {
    Component: GomNotificationListener,
    unique: true,   // ⭐ Prevent duplicate notifications
});
