import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { api } from "./api";
import {
  announceBrowserSession,
  isStaff,
  observeBrowserSession,
} from "./browserSession";
import { t } from "./i18n";
import { preferences } from "./preferences";

export function useAdminWorkspace() {
  const user = ref(null);
  const initial = ref(true);
  const busy = ref(false);
  const error = ref("");
  const view = ref("overview");
  const operations = ref({});
  const menus = ref([]);
  const members = ref([]);
  const memberPage = ref({ q: "", offset: 0, newest: false, hasMore: false });
  const tutorial = ref(false);
  const basicKeys = ["overview", "trips", "logs", "tests", "codes"];
  const adminKeys = ["members", "menu"];
  const admin = computed(() => user.value?.role === "ADMIN");
  let workspaceRead = 0;

  const menuItems = computed(() => {
    const review = admin.value && operations.value.demo === true;
    let keys = [
      ...basicKeys,
      ...(admin.value ? adminKeys : []),
      ...(review ? ["scenarioReview"] : []),
      "settings",
    ];
    const configured = new Map(menus.value.map((item) => [item.key, item]));
    keys = keys.filter(
      (key) => key === "settings" || configured.get(key)?.visible !== false,
    );
    return keys
      .map((key, i) => ({
        key,
        position: configured.get(key)?.position ?? (i + 1) * 10,
        label:
          configured.get(key)?.[
            { ko: "labelKo", en: "labelEn", "zh-Hans": "labelZh" }[
              preferences.locale
            ]
          ] || t(key),
      }))
      .sort((left, right) => left.position - right.position);
  });

  async function request(path) {
    const read = ++workspaceRead;
    const owner = user.value;
    const screen = view.value;
    const current = () =>
      read === workspaceRead && user.value === owner && view.value === screen;
    busy.value = true;
    error.value = "";
    try {
      const data = await api(path);
      return current() ? data : undefined;
    } catch (err) {
      if (current()) {
        if (err.status === 401) clearAccount();
        error.value = err.status === 403 ? "denied" : "error";
      }
    } finally {
      if (read === workspaceRead) busy.value = false;
    }
  }

  async function refresh() {
    if (!user.value) return;
    if (view.value === "members" && admin.value) {
      const { q, offset, newest } = memberPage.value;
      const query = new URLSearchParams({ q, offset, newest, limit: 50 });
      const data = await request("/admin/members/page?" + query);
      if (data) {
        members.value = data.items;
        memberPage.value.hasMore = data.hasMore;
      }
    } else if (view.value === "menu" && admin.value) {
      const data = await request("/admin/menu");
      if (data) menus.value = data;
    } else if (!["settings", "scenarioReview"].includes(view.value)) {
      const data = await request("/operations");
      if (data) operations.value = data;
    }
  }

  function browseMembers(filters) {
    memberPage.value = { ...memberPage.value, ...filters };
    return refresh();
  }

  function clearAccount() {
    workspaceRead += 1;
    tutorial.value = false;
    busy.value = false;
    view.value = "overview";
    user.value = null;
    operations.value = {};
    members.value = [];
    memberPage.value = { q: "", offset: 0, newest: false, hasMore: false };
    menus.value = [];
  }

  async function signed(account) {
    if (!isStaff(account)) return;
    if (user.value?.id === account.id && user.value.role === account.role)
      return;
    clearAccount();
    user.value = account;
    view.value = "overview";
    tutorial.value = preferences.tutorialEnabled && !preferences.tutorialSeen;
    await refresh();
    const data = await api(admin.value ? "/admin/menu" : "/menu").catch(
      () => [],
    );
    if (user.value?.id === account.id && Array.isArray(data))
      menus.value = data;
  }

  async function signOut() {
    try {
      await api("/auth/logout", { method: "POST" });
      clearAccount();
      announceBrowserSession();
    } catch {
      error.value = "error";
    }
  }

  function show(key) {
    if (adminKeys.includes(key) && !admin.value) return;
    if (
      key === "scenarioReview" &&
      (!admin.value || operations.value.demo !== true)
    )
      return;
    view.value = key;
  }

  let stopObserving;
  let sessionRead = 0;

  async function refreshSession() {
    const read = ++sessionRead;
    try {
      const account = await api("/auth/me");
      if (read !== sessionRead) return;
      if (isStaff(account)) await signed(account);
      else if (user.value) clearAccount();
    } catch (failure) {
      if (read === sessionRead && failure.status === 401 && user.value)
        clearAccount();
    } finally {
      if (read === sessionRead) initial.value = false;
    }
  }

  onMounted(() => {
    stopObserving = observeBrowserSession(refreshSession);
    refreshSession();
  });
  onBeforeUnmount(() => stopObserving?.());
  watch(view, refresh);

  return {
    user,
    initial,
    busy,
    error,
    view,
    operations,
    menus,
    members,
    memberPage,
    browseMembers,
    tutorial,
    admin,
    menuItems,
    refresh,
    signed,
    signOut,
    show,
  };
}
