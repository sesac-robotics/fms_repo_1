<script setup>
import { ref } from "vue";
import { api } from "../api";
import { t } from "../i18n";

defineProps({ items: { type: Array, required: true } });
const emit = defineEmits(["changed"]);
const pending = ref(null);
const message = ref("");

async function review(id, approved, role) {
  pending.value = id;
  message.value = "";
  try {
    await api("/admin/members/" + encodeURIComponent(id) + "/approval", {
      method: "PUT",
      body: { approved, ...(approved ? { role } : {}) },
    });
    message.value = "saved";
    emit("changed");
  } catch (error) {
    message.value = error.status === 403 ? "denied" : "error";
  } finally {
    pending.value = null;
  }
}

function approve(id, event) {
  review(id, true, new FormData(event.currentTarget).get("role"));
}
</script>

<template>
  <section class="panel">
    <h2>{{ t("members") }}</h2>
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
              <span v-else>—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
