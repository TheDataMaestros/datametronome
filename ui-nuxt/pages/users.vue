<template>
  <div class="space-y-6">
    <div>
      <p class="dm-label mb-2">Administration</p>
      <h1
        style="font-family: var(--dm-font-display); font-size: 2.4rem; font-weight: 700; letter-spacing: -0.03em; color: var(--dm-text-primary); line-height: 1.15;"
      >
        Users
      </h1>
    </div>

    <!-- Admin gate -->
    <div v-if="!isAdmin" class="intelligence-panel rounded-xl p-6 text-center">
      <Icon name="i-heroicons-lock-closed" class="w-8 h-8 text-slate-500 mx-auto mb-3" />
      <p class="text-slate-400 text-sm">Only administrators can manage users.</p>
    </div>

    <template v-else>
      <!-- Users Table -->
      <div class="intelligence-panel rounded-xl p-5">
        <div class="flex items-center justify-between mb-5">
          <div class="flex items-center gap-2">
            <Icon name="i-heroicons-users" class="w-5 h-5 text-blue-400" />
            <p class="text-base font-semibold text-white">User Accounts</p>
            <span class="text-xs text-slate-500">{{ users.length }} total</span>
          </div>
          <button
            class="px-4 py-2 rounded-lg text-sm font-medium bg-blue-600 hover:bg-blue-500 text-white transition-colors flex items-center gap-1.5"
            @click="openCreateModal"
          >
            <Icon name="i-heroicons-plus" class="w-4 h-4" />
            Create User
          </button>
        </div>

        <div v-if="loading" class="text-center py-8 text-slate-500 text-sm">Loading users...</div>

        <div v-else-if="users.length === 0" class="text-center py-8 text-slate-500 text-sm">
          No users found.
        </div>

        <div v-else class="overflow-x-auto">
          <table class="w-full text-base">
            <thead>
              <tr class="text-left text-xs text-slate-500 uppercase tracking-wider border-b border-slate-700/50">
                <th class="pb-3 pr-4">Username</th>
                <th class="pb-3 pr-4">Email</th>
                <th class="pb-3 pr-4">Role</th>
                <th class="pb-3 pr-4">Status</th>
                <th class="pb-3 pr-4">Created</th>
                <th class="pb-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="u in users"
                :key="u.id"
                class="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors"
              >
                <td class="py-3 pr-4 text-white font-medium">{{ u.username }}</td>
                <td class="py-3 pr-4 text-slate-400">{{ u.email }}</td>
                <td class="py-3 pr-4">
                  <span
                    class="inline-block px-2.5 py-0.5 rounded text-xs font-semibold uppercase tracking-wide"
                    :class="roleBadgeClass(u.role)"
                  >
                    {{ u.role }}
                  </span>
                </td>
                <td class="py-3 pr-4">
                  <span
                    class="inline-flex items-center gap-1.5 text-sm"
                    :class="u.is_active ? 'text-emerald-400' : 'text-slate-500'"
                  >
                    <span class="w-2 h-2 rounded-full" :class="u.is_active ? 'bg-emerald-400' : 'bg-slate-600'" />
                    {{ u.is_active ? 'Active' : 'Inactive' }}
                  </span>
                </td>
                <td class="py-3 pr-4 text-slate-500 text-sm">{{ formatDate(u.created_at) }}</td>
                <td class="py-3 text-right">
                  <div class="flex items-center justify-end gap-1.5">
                    <button
                      class="p-1.5 rounded hover:bg-slate-700/50 text-slate-500 hover:text-white transition-colors"
                      title="Edit user"
                      @click="openEditModal(u)"
                    >
                      <Icon name="i-heroicons-pencil-square" class="w-4 h-4" />
                    </button>
                    <button
                      class="p-1.5 rounded hover:bg-slate-700/50 text-slate-500 hover:text-white transition-colors"
                      title="Reset password"
                      @click="openResetModal(u)"
                    >
                      <Icon name="i-heroicons-key" class="w-4 h-4" />
                    </button>
                    <button
                      class="p-1.5 rounded hover:bg-slate-700/50 text-slate-500 hover:text-red-400 transition-colors"
                      :class="{ 'opacity-30 pointer-events-none': isSelf(u) }"
                      :disabled="isSelf(u)"
                      title="Delete user"
                      @click="openDeleteModal(u)"
                    >
                      <Icon name="i-heroicons-trash" class="w-4 h-4" />
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Feedback message -->
        <p v-if="feedbackMsg" class="text-sm mt-3" :class="feedbackError ? 'text-red-400' : 'text-emerald-400'">
          {{ feedbackMsg }}
        </p>
      </div>

      <!-- Create User Modal -->
      <Teleport to="body">
        <div v-if="showCreate" class="dm-modal-overlay" @click.self="showCreate = false">
          <div class="dm-modal">
            <h3 class="text-base font-semibold text-white mb-4">Create User</h3>
            <div class="space-y-3">
              <div>
                <label class="block text-sm text-slate-400 mb-1">Username</label>
                <input v-model="createForm.username" type="text" class="dm-input" placeholder="johndoe" />
              </div>
              <div>
                <label class="block text-sm text-slate-400 mb-1">Email</label>
                <input v-model="createForm.email" type="email" class="dm-input" placeholder="john@example.com" />
              </div>
              <div>
                <label class="block text-sm text-slate-400 mb-1">Password</label>
                <input v-model="createForm.password" type="password" class="dm-input" placeholder="Min 8 characters" />
              </div>
              <div>
                <label class="block text-sm text-slate-400 mb-1">Role</label>
                <select v-model="createForm.role" class="dm-input">
                  <option value="viewer">Viewer</option>
                  <option value="editor">Editor</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
            </div>
            <p v-if="modalError" class="text-sm text-red-400 mt-2">{{ modalError }}</p>
            <div class="flex justify-end gap-2 mt-4">
              <button class="dm-btn-secondary" @click="showCreate = false">Cancel</button>
              <button class="dm-btn-primary" :disabled="modalSaving" @click="handleCreate">
                {{ modalSaving ? 'Creating...' : 'Create' }}
              </button>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Edit User Modal -->
      <Teleport to="body">
        <div v-if="showEdit" class="dm-modal-overlay" @click.self="showEdit = false">
          <div class="dm-modal">
            <h3 class="text-base font-semibold text-white mb-4">Edit User: {{ editTarget?.username }}</h3>
            <div class="space-y-3">
              <div>
                <label class="block text-sm text-slate-400 mb-1">Email</label>
                <input v-model="editForm.email" type="email" class="dm-input" />
              </div>
              <div>
                <label class="block text-sm text-slate-400 mb-1">Role</label>
                <select v-model="editForm.role" class="dm-input" :disabled="isSelf(editTarget!)">
                  <option value="viewer">Viewer</option>
                  <option value="editor">Editor</option>
                  <option value="admin">Admin</option>
                </select>
              </div>
              <div class="flex items-center gap-2">
                <label class="text-sm text-slate-400">Active</label>
                <button
                  class="w-9 h-5 rounded-full transition-colors relative"
                  :class="editForm.is_active ? 'bg-emerald-600' : 'bg-slate-700'"
                  :disabled="isSelf(editTarget!)"
                  @click="editForm.is_active = !editForm.is_active"
                >
                  <span
                    class="absolute top-0.5 w-4 h-4 rounded-full bg-white transition-transform"
                    :class="editForm.is_active ? 'left-[18px]' : 'left-0.5'"
                  />
                </button>
              </div>
            </div>
            <p v-if="modalError" class="text-sm text-red-400 mt-2">{{ modalError }}</p>
            <div class="flex justify-end gap-2 mt-4">
              <button class="dm-btn-secondary" @click="showEdit = false">Cancel</button>
              <button class="dm-btn-primary" :disabled="modalSaving" @click="handleEdit">
                {{ modalSaving ? 'Saving...' : 'Save' }}
              </button>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Reset Password Modal -->
      <Teleport to="body">
        <div v-if="showReset" class="dm-modal-overlay" @click.self="showReset = false">
          <div class="dm-modal">
            <h3 class="text-base font-semibold text-white mb-4">Reset Password: {{ resetTarget?.username }}</h3>
            <div>
              <label class="block text-sm text-slate-400 mb-1">New Password</label>
              <input v-model="resetPassword" type="password" class="dm-input" placeholder="Min 8 characters" />
            </div>
            <p v-if="modalError" class="text-sm text-red-400 mt-2">{{ modalError }}</p>
            <div class="flex justify-end gap-2 mt-4">
              <button class="dm-btn-secondary" @click="showReset = false">Cancel</button>
              <button class="dm-btn-primary" :disabled="modalSaving" @click="handleReset">
                {{ modalSaving ? 'Resetting...' : 'Reset Password' }}
              </button>
            </div>
          </div>
        </div>
      </Teleport>

      <!-- Delete Confirmation Modal -->
      <Teleport to="body">
        <div v-if="showDelete" class="dm-modal-overlay" @click.self="showDelete = false">
          <div class="dm-modal">
            <h3 class="text-base font-semibold text-white mb-2">Delete User</h3>
            <p class="text-sm text-slate-400 mb-4">
              Are you sure you want to {{ hardDelete ? 'permanently delete' : 'deactivate' }}
              <span class="text-white font-medium">{{ deleteTarget?.username }}</span>?
            </p>
            <div class="flex items-center gap-2 mb-4">
              <input id="hard-delete" v-model="hardDelete" type="checkbox" class="rounded border-slate-600" />
              <label for="hard-delete" class="text-sm text-slate-400">Permanently delete (cannot be undone)</label>
            </div>
            <p v-if="modalError" class="text-sm text-red-400 mt-2">{{ modalError }}</p>
            <div class="flex justify-end gap-2">
              <button class="dm-btn-secondary" @click="showDelete = false">Cancel</button>
              <button
                class="px-4 py-2 rounded-lg text-sm font-medium transition-colors"
                :class="hardDelete ? 'bg-red-600 hover:bg-red-500 text-white' : 'bg-amber-600 hover:bg-amber-500 text-white'"
                :disabled="modalSaving"
                @click="handleDelete"
              >
                {{ modalSaving ? 'Deleting...' : (hardDelete ? 'Delete Permanently' : 'Deactivate') }}
              </button>
            </div>
          </div>
        </div>
      </Teleport>
    </template>
  </div>
</template>

<script setup lang="ts">
import { usersService, type UserDetail } from '~/services/users'
import { extractErrorMessage } from '~/services/api'

definePageMeta({ middleware: 'auth', layout: 'dashboard' })
useHead({ title: 'Users - DataMetronome' })

const authStore = useAuthStore()
const isAdmin = computed(() => authStore.user?.role === 'admin')

const loading = ref(true)
const users = ref<UserDetail[]>([])
const feedbackMsg = ref('')
const feedbackError = ref(false)

// Modal state
const showCreate = ref(false)
const showEdit = ref(false)
const showReset = ref(false)
const showDelete = ref(false)
const modalSaving = ref(false)
const modalError = ref('')

// Create form
const createForm = reactive({ username: '', email: '', password: '', role: 'viewer' as const })

// Edit form
const editTarget = ref<UserDetail | null>(null)
const editForm = reactive({ email: '', role: 'viewer' as 'admin' | 'editor' | 'viewer', is_active: true })

// Reset
const resetTarget = ref<UserDetail | null>(null)
const resetPassword = ref('')

// Delete
const deleteTarget = ref<UserDetail | null>(null)
const hardDelete = ref(false)

function isSelf(u: UserDetail) {
  return u.username === authStore.user?.username
}

function roleBadgeClass(role: string) {
  switch (role) {
    case 'admin': return 'bg-purple-500/20 text-purple-300'
    case 'editor': return 'bg-blue-500/20 text-blue-300'
    default: return 'bg-slate-500/20 text-slate-400'
  }
}

function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })
  } catch { return iso }
}

function showFeedback(msg: string, isError = false) {
  feedbackMsg.value = msg
  feedbackError.value = isError
  setTimeout(() => { feedbackMsg.value = '' }, 4000)
}

async function loadUsers() {
  loading.value = true
  try {
    users.value = await usersService.getAll()
  } catch (err) {
    showFeedback(extractErrorMessage(err, 'Failed to load users'), true)
  } finally {
    loading.value = false
  }
}

// Create
function openCreateModal() {
  createForm.username = ''
  createForm.email = ''
  createForm.password = ''
  createForm.role = 'viewer'
  modalError.value = ''
  showCreate.value = true
}

async function handleCreate() {
  modalSaving.value = true
  modalError.value = ''
  try {
    await usersService.create(createForm)
    showCreate.value = false
    showFeedback('User created successfully')
    await loadUsers()
  } catch (err) {
    modalError.value = extractErrorMessage(err, 'Failed to create user')
  } finally {
    modalSaving.value = false
  }
}

// Edit
function openEditModal(u: UserDetail) {
  editTarget.value = u
  editForm.email = u.email
  editForm.role = u.role
  editForm.is_active = u.is_active
  modalError.value = ''
  showEdit.value = true
}

async function handleEdit() {
  if (!editTarget.value) return
  modalSaving.value = true
  modalError.value = ''
  try {
    const payload: Record<string, any> = {}
    if (editForm.email !== editTarget.value.email) payload.email = editForm.email
    if (editForm.role !== editTarget.value.role) payload.role = editForm.role
    if (editForm.is_active !== editTarget.value.is_active) payload.is_active = editForm.is_active
    if (Object.keys(payload).length === 0) {
      showEdit.value = false
      return
    }
    await usersService.update(editTarget.value.id, payload)
    showEdit.value = false
    showFeedback('User updated successfully')
    await loadUsers()
  } catch (err) {
    modalError.value = extractErrorMessage(err, 'Failed to update user')
  } finally {
    modalSaving.value = false
  }
}

// Reset password
function openResetModal(u: UserDetail) {
  resetTarget.value = u
  resetPassword.value = ''
  modalError.value = ''
  showReset.value = true
}

async function handleReset() {
  if (!resetTarget.value) return
  modalSaving.value = true
  modalError.value = ''
  try {
    await usersService.resetPassword(resetTarget.value.id, resetPassword.value)
    showReset.value = false
    showFeedback('Password reset successfully')
  } catch (err) {
    modalError.value = extractErrorMessage(err, 'Failed to reset password')
  } finally {
    modalSaving.value = false
  }
}

// Delete
function openDeleteModal(u: UserDetail) {
  deleteTarget.value = u
  hardDelete.value = false
  modalError.value = ''
  showDelete.value = true
}

async function handleDelete() {
  if (!deleteTarget.value) return
  modalSaving.value = true
  modalError.value = ''
  try {
    await usersService.remove(deleteTarget.value.id, hardDelete.value)
    showDelete.value = false
    showFeedback(hardDelete.value ? 'User permanently deleted' : 'User deactivated')
    await loadUsers()
  } catch (err) {
    modalError.value = extractErrorMessage(err, 'Failed to delete user')
  } finally {
    modalSaving.value = false
  }
}

onMounted(() => {
  if (isAdmin.value) loadUsers()
  else loading.value = false
})
</script>

<style scoped>
.dm-modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
}
.dm-modal {
  background: #1e293b;
  border: 1px solid #334155;
  border-radius: 12px;
  padding: 20px;
  width: 100%;
  max-width: 420px;
}
.dm-input {
  width: 100%;
  background: #0f1117;
  border: 1px solid #334155;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 18.2px;
  color: #e2e8f0;
  outline: none;
  transition: border-color 0.15s;
}
.dm-input:focus {
  border-color: #3b82f6;
}
.dm-btn-primary {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 16.9px;
  font-weight: 600;
  background: #3b82f6;
  color: white;
  transition: background 0.15s;
}
.dm-btn-primary:hover:not(:disabled) { background: #2563eb; }
.dm-btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.dm-btn-secondary {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 16.9px;
  color: #94a3b8;
  border: 1px solid #334155;
  transition: all 0.15s;
}
.dm-btn-secondary:hover { color: white; border-color: #475569; }
</style>
