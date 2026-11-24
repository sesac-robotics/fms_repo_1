<script setup>
import { ref } from "vue";
import { api } from "../api";
import { t } from "../i18n";

defineProps({
  items: { type: Array, required: true },
  page: { type: Object, required: true },
  loading: Boolean,
});
const emit = defineEmits(["changed", "browse"]);
const pending = ref(null);
const message = ref("");

function search(event) {
  const data = new FormData(event.currentTarget);
  emit("browse", {
    q: String(data.get("q")).trim(),
    newest: data.get("order") === "newest",
    offset: 0,
  });
}

async function updateMember(id, operation, body) {
  pending.value = id;
  message.value = "";
  try {
    await api("/admin/members/" + encodeURIComponent(id) + "/" + operation, {
      method: "PUT",
      body,
    });
    message.value = "saved";
    emit("changed");
  } catch (error) {
    message.value = error.status === 403 ? "denied" : "error";
  } finally {
    pending.value = null;
  }
}

function review(id, approved, role) {
  return updateMember(id, "approval", {
    approved,
    ...(approved ? { role } : {}),
  });
}

function addOperator(item) {
  if (window.confirm(`${t("addGoogleOperator")} · ${item.email}?`))
    updateMember(item.id, "google-operator");
}

function approve(id, event) {
  review(id, true, new FormData(event.currentTarget).get("role"));
}
</script>

<template>
  <section class="panel">
    <h2>{{ t("members") }}</h2>
    <form class="actions" @submit.prevent="search">
      <label
        >{{ t("memberSearch") }}
        <input name="q" maxlength="100" :value="page.q"
      /></label>
      <label
        >{{ t("order") }}
        <select name="order" :value="page.newest ? 'newest' : 'oldest'">
          <option value="oldest">{{ t("oldestFirst") }}</option>
          <option value="newest">{{ t("newestFirst") }}</option>
        </select>
      </label>
      <button :disabled="loading">{{ t("memberSearch") }}</button>
    </form>
    <div class="actions">
      <button
        type="button"
        :disabled="loading || page.offset === 0"
        @click="$emit('browse', { offset: Math.max(0, page.offset - 50) })"
      >
        {{ t("previousPage") }}
      </button>
      <button
        type="button"
        :disabled="loading || !page.hasMore"
        @click="$emit('browse', { offset: page.offset + 50 })"
      >
        {{ t("next") }}
      </button>
    </div>
    <p v-if="message" role="status">{{ t(message) }}</p>
    <p v-if="!items.length">{{ t("empty") }}</p>
    <div v-else class="table-scroll">
      <table>
        <thead>
          <tr>
            <th>{{ t("name") }}</th>
            <th>{{ t("email") }}</th>
            <th>{{ t("role") }}</th>
            <th>{{ t("accountState") }}</th>
            <th>{{ t("approval") }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in items" :key="item.id">
            <td>{{ item.name }}</td>
            <td>{{ item.email }}</td>
            <td>{{ t(item.role) }}</td>
            <td>{{ t(item.status) }}</td>
            <td>
              <form
                v-if="item.status === 'PENDING' && item.role !== 'PASSENGER'"
                class="actions"
                @submit.prevent="approve(item.id, $event)"
              >
                <select name="role" :aria-label="t('role')">
                  <option value="ADMIN">
                    {{ t("ADMIN") }}
                  </option>
                  <option value="OPERATOR">
                    {{ t("OPERATOR") }}
                  </option>
                </select>
                <button class="primary" :disabled="pending !== null">
                  {{ t("approval") }}
                </button>
                <button
                  type="button"
                  :disabled="pending !== null"
                  @click="review(item.id, false)"
                >
                  {{ t("reject") }}
                </button>
              </form>
              <button
                v-else-if="
                  item.status === 'ACTIVE' && item.role === 'PASSENGER'
                "
                type="button"
                :disabled="pending !== null"
                @click="addOperator(item)"
              >
                {{ t("addGoogleOperator") }}
              </button>
              <span v-else>—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
