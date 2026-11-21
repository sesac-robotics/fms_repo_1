const channelName = "amo-admin-cookie-changed";
const signal = "session";

export function isStaff(user) {
    return user?.role === "ADMIN" || user?.role === "OPERATOR";
}

/** Notifies sibling tabs to recheck the HttpOnly cookie without exchanging data. */
export function announceBrowserSession() {
    if (typeof BroadcastChannel === "undefined") return;
    const channel = new BroadcastChannel(channelName);
    channel.postMessage(signal);
    channel.close();
}

export function observeBrowserSession(refresh) {
    const channel =
        typeof BroadcastChannel === "undefined"
            ? null
            : new BroadcastChannel(channelName);
    const receive = ({ data }) => {
        if (data === signal) refresh();
    };
    channel?.addEventListener("message", receive);
    window.addEventListener("focus", refresh);
    return () => {
        channel?.close();
        window.removeEventListener("focus", refresh);
    };
}
