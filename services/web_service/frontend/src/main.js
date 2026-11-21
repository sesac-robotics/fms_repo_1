import { createApp } from "vue";
import App from "./App.vue";
import DesktopSignIn from "./views/DesktopSignIn.vue";
import "./theme.css";
import "./layout.css";
import "./components.css";
import "./route-map.css";
createApp(
    window.location.pathname === "/desktop-sign-in" ? DesktopSignIn : App,
).mount("#app");
