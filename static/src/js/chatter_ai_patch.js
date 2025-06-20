/** @odoo-module **/

import { Chatter } from "@mail/chatter/web_portal/chatter";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { convertBrToLineBreak } from "@mail/utils/common/format";
import { registry } from "@web/core/registry";

// Store the original method before patching
const originalOnClickAIChatterButton = Chatter.prototype.onClickAIChatterButton;

patch(Chatter.prototype, {
    setup() {
        super.setup();
        this.actionService = useService("action");
        // Only try to get aiChatLauncher if it exists
        try {
            this.aiChatLauncher = useService("aiChatLauncher");
        } catch (error) {
            console.warn("aiChatLauncher service not available:", error);
            this.aiChatLauncher = null;
        }
    },

    async onClickAIChatterButton() {
        console.log("AI Document Extraction: Intercepting AI chatter button click!");
        
        try {
            // Force save the record so we can fetch chatter messages from the back-end
            if (this.props.record && this.props.record.save) {
                const saved = await this.props.record.save();
                if (!saved) {
                    return;
                }
            }

            console.log("AI Document Extraction: Opening agent selection wizard...");
            
            // Open agent selection wizard instead of default AI chat
            // Prepare safe parameters without circular references
            const safeParams = {
                callerComponentName: 'chatter_ai_button',
                originalRecordModel: this.props.record?.resModel || this.props.threadModel,
                originalRecordId: this.props.record?.resId || this.props.threadId,
                aiChatSourceId: this.props.record?.resId || this.props.threadId,
                placeholderPrompt: _t("Summarize the chatter conversation"),
            };

            // Ensure we have valid IDs (convert to integers if needed)
            if (safeParams.originalRecordId) {
                safeParams.originalRecordId = parseInt(safeParams.originalRecordId);
                safeParams.aiChatSourceId = parseInt(safeParams.aiChatSourceId);
            }

            // Only include basic record data to avoid circular references
            if (this.props.record?.data) {
                safeParams.originalRecordData = {};
                // Only include simple, safe fields
                const safeFields = ['name', 'display_name', 'email', 'phone', 'mobile'];
                for (const field of safeFields) {
                    if (this.props.record.data[field] && typeof this.props.record.data[field] === 'string') {
                        safeParams.originalRecordData[field] = this.props.record.data[field];
                    }
                }
            }

            const action = {
                type: "ir.actions.act_window",
                res_model: "choose.agent.wizard",
                views: [[false, "form"]],
                target: "new",
                context: {
                    default_original_params: JSON.stringify(safeParams),
                },
            };
            
            await this.actionService.doAction(action);
            
        } catch (error) {
            console.error("Error opening agent selection wizard:", error);
            
            // Fall back to original behavior if our code fails and aiChatLauncher is available
            if (this.aiChatLauncher) {
                console.log("Falling back to default AI behavior");
                try {
                    await this.aiChatLauncher.openAIChatFromContextV2({
                        callerComponentName: 'chatter_ai_button',
                        originalRecordModel: this.props.record?.resModel || this.props.threadModel,
                        originalRecordId: this.props.record?.resId || this.props.threadId,
                        originalRecordData: this.props.record?.data,
                        originalRecordFields: this.props.record?.fields,
                        aiChatSourceId: this.props.record?.resId || this.props.threadId,
                        specialActionCallbacks: {
                            sendMessage: (content) => {
                                if (this.state?.thread?.composer) {
                                    this.state.thread.composer.text = convertBrToLineBreak(content);
                                    this.toggleComposer('message');
                                }
                            },
                            logNote: (content) => {
                                if (this.state?.thread?.composer) {
                                    this.state.thread.composer.text = convertBrToLineBreak(content);
                                    this.toggleComposer('note');
                                }
                            }
                        },
                        placeholderPrompt: _t("Summarize the chatter conversation"),
                    });
                } catch (fallbackError) {
                    console.error("Fallback also failed:", fallbackError);
                }
            }
        }
    },
});

/**
 * Client action to open the original AI chat
 * This directly calls the original onClickAIChatterButton method
 */
function openOriginalAIChat(env, action) {
    const params = action.params || {};
    
    console.log("AI Document Extraction: Opening original AI chat with params:", params);
    
    try {
        const aiChatLauncherService = env.services.aiChatLauncher;
        
        if (!aiChatLauncherService) {
            env.services.notification.add("AI Chat service not available", { type: "warning" });
            return;
        }

        // Call the original AI chat launcher exactly as the enterprise module does
        aiChatLauncherService.openAIChatFromContextV2({
            callerComponentName: 'chatter_ai_button',
            originalRecordModel: params.originalRecordModel,
            originalRecordId: params.originalRecordId,
            originalRecordData: params.originalRecordData || {},
            originalRecordFields: params.originalRecordFields || {},
            aiChatSourceId: params.aiChatSourceId || params.originalRecordId,
            specialActionCallbacks: {
                sendMessage: (content) => {
                    console.log("Send message:", content);
                },
                logNote: (content) => {
                    console.log("Log note:", content);
                }
            },
            placeholderPrompt: params.placeholderPrompt || _t("Summarize the chatter conversation"),
        });

    } catch (error) {
        console.error("AI Document Extraction: Error opening original AI chat:", error);
        env.services.notification.add(
            "Failed to open AI chat: " + (error.message || error),
            { type: "danger" }
        );
    }
}

// Register the client action
registry.category("actions").add("open_original_ai_chat", openOriginalAIChat);

// Client action to trigger original AI chat functionality
function triggerOriginalAIChat(env, action) {
    const params = action.params || {};
    
    console.log("AI Document Extraction: Triggering original AI chat with params:", params);
    
    try {
        // Get the AI chat launcher service
        const aiChatLauncherService = env.services.aiChatLauncher;
        
        if (!aiChatLauncherService) {
            env.services.notification.add("AI Chat service not available", { type: "warning" });
            return;
        }

        // Use the original AI chat functionality
        aiChatLauncherService.openAIChatFromContextV2({
            callerComponentName: params.callerComponentName || 'chatter_ai_button',
            originalRecordModel: params.originalRecordModel,
            originalRecordId: params.originalRecordId,
            originalRecordData: params.originalRecordData || {},
            aiChatSourceId: params.aiChatSourceId,
            specialActionCallbacks: {
                sendMessage: (content) => {
                    console.log("Send message:", content);
                },
                logNote: (content) => {
                    console.log("Log note:", content);
                }
            },
            placeholderPrompt: params.placeholderPrompt || "Ask me anything",
        });

    } catch (error) {
        console.error("AI Document Extraction: Error opening original AI chat:", error);
        env.services.notification.add(
            "Failed to open AI chat: " + (error.message || error),
            { type: "danger" }
        );
    }
}

// Register the client action for triggering original AI chat
registry.category("actions").add("trigger_original_ai_chat", triggerOriginalAIChat);

// Simple client action to close dialog and open AI chat
function closeDialogAndOpenChat(env, action) {
    const params = action.params || {};
    
    console.log("AI Document Extraction: Closing dialog and opening AI chat");
    
    // Close any open dialogs
    if (env.services.dialog) {
        env.services.dialog.closeAll();
    }
    
    // Small delay to ensure dialog is closed, then open AI chat
    setTimeout(() => {
        try {
            const aiChatLauncherService = env.services.aiChatLauncher;
            
            if (!aiChatLauncherService) {
                env.services.notification.add("AI Chat service not available", { type: "warning" });
                return;
            }

            // Call the original AI chat launcher
            aiChatLauncherService.openAIChatFromContextV2({
                callerComponentName: 'chatter_ai_button',
                originalRecordModel: params.originalRecordModel,
                originalRecordId: params.originalRecordId,
                originalRecordData: params.originalRecordData || {},
                originalRecordFields: params.originalRecordFields || {},
                aiChatSourceId: params.aiChatSourceId || params.originalRecordId,
                specialActionCallbacks: {
                    sendMessage: (content) => {
                        console.log("Send message:", content);
                    },
                    logNote: (content) => {
                        console.log("Log note:", content);
                    }
                },
                placeholderPrompt: params.placeholderPrompt || _t("Summarize the chatter conversation"),
            });

        } catch (error) {
            console.error("AI Document Extraction: Error opening AI chat:", error);
            env.services.notification.add(
                "Failed to open AI chat: " + (error.message || error),
                { type: "danger" }
            );
        }
    }, 100); // Small delay to ensure dialog closes first
}

registry.category("actions").add("close_dialog_and_open_chat", closeDialogAndOpenChat);
