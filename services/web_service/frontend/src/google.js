let scriptLoad;

function loadIdentity() {
    if (window.google?.accounts?.id)
        return Promise.resolve(window.google.accounts.id);
    if (!scriptLoad) {
        scriptLoad = new Promise((resolve, reject) => {
            const script = document.createElement("script");
            script.src = "https://accounts.google.com/gsi/client";
            script.async = true;
            script.onload = () =>
                window.google?.accounts?.id
                    ? resolve(window.google.accounts.id)
                    : reject(new Error("Identity library unavailable"));
            script.onerror = () => {
                script.remove();
                scriptLoad = undefined;
                reject(new Error("Identity library unavailable"));
            };
            document.head.append(script);
        });
    }
    return scriptLoad;
}

export async function installGoogleButton(
    element,
    { clientId, locale, theme, credential },
) {
    const identity = await loadIdentity();
    identity.initialize({
        client_id: clientId,
        callback: ({ credential: token }) => credential(token),
    });
    element.replaceChildren();
    identity.renderButton(element, {
        theme: theme === "dark" ? "filled_black" : "outline",
        locale: locale === "zh-Hans" ? "zh_CN" : locale,
        size: "large",
        shape: "pill",
    });
}
