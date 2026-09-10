const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];
const categories = [
  "Food",
  "Transport",
  "Shopping",
  "Bills",
  "Health",
  "Entertainment",
  "Education",
  "Salary",
  "Other",
];
const state = {
  token: localStorage.getItem("finwise_token"),
  user: null,
  accounts: [],
  cards: [],
  transactions: [],
  summary: null,
  authMode: "register",
};

function currency(value) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: state.user?.currency || "INR",
    maximumFractionDigits: 2,
  }).format(value || 0);
}

function escapeHtml(value) {
  const node = document.createElement("div");
  node.textContent = value ?? "";
  return node.innerHTML;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
      ...options.headers,
    },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = Array.isArray(body.detail)
      ? body.detail[0]?.msg
      : body.detail;
    throw new Error(detail || "Request failed");
  }
  return response.status === 204 ? null : response.json();
}

function toast(message) {
  const node = $("#toast");
  node.textContent = message;
  node.style.display = "block";
  setTimeout(() => {
    node.style.display = "none";
  }, 2200);
}

function showApp(authenticated) {
  $("#auth-view").classList.toggle("hidden", authenticated);
  $("#app-view").classList.toggle("hidden", !authenticated);
}

async function authenticate(event) {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(event.currentTarget));
  const path =
    state.authMode === "register" ? "/api/auth/register" : "/api/auth/login";
  try {
    const result = await api(path, {
      method: "POST",
      body: JSON.stringify(values),
    });
    state.token = result.token;
    localStorage.setItem("finwise_token", state.token);
    await initialize();
  } catch (error) {
    $("#auth-error").textContent = error.message;
  }
}

function toggleAuth() {
  state.authMode = state.authMode === "register" ? "login" : "register";
  const registering = state.authMode === "register";
  $("#name-label").classList.toggle("hidden", !registering);
  $("#auth-title").textContent = registering
    ? "Create your account"
    : "Welcome back";
  $("#auth-submit").textContent = registering ? "Create account" : "Sign in";
  $("#auth-toggle").textContent = registering
    ? "Already registered? Sign in"
    : "New to FinWise? Create account";
  $("#auth-error").textContent = "";
}

async function initialize() {
  if (!state.token) return showApp(false);
  try {
    state.user = await api("/api/me");
    showApp(true);
    $("#sidebar-name").textContent = state.user.name;
    $("#welcome-name").textContent = state.user.name.split(" ")[0];
    await refreshAll();
    populateSettings();
  } catch {
    logout();
  }
}

async function refreshAll() {
  [state.accounts, state.cards, state.summary] = await Promise.all([
    api("/api/accounts"),
    api("/api/cards"),
    api("/api/dashboard"),
  ]);
  const result = await api(buildTransactionUrl());
  state.transactions = result.items;
  renderDashboard();
  renderTransactions(result.total);
  renderAccounts();
  renderAnalytics();
}

function buildTransactionUrl() {
  const params = new URLSearchParams();
  if ($("#kind-filter").value) params.set("kind", $("#kind-filter").value);
  if ($("#category-filter").value)
    params.set("category", $("#category-filter").value);
  if ($("#search").value) params.set("search", $("#search").value);
  return `/api/transactions?${params}`;
}

function renderDashboard() {
  const data = state.summary;
  $("#net").textContent = currency(data.net);
  $("#income").textContent = currency(data.income);
  $("#spent").textContent = currency(data.spent);
  $("#balance").textContent = currency(data.accounts_total);
  $("#insight").textContent = data.insight;
  renderBars($("#category-chart"), data.categories, "name");
  $("#recent-list").innerHTML = state.transactions.length
    ? state.transactions.slice(0, 5).map(transactionRow).join("")
    : '<p class="empty">No transactions yet.</p>';
}

function transactionRow(item) {
  const symbol =
    item.kind === "income" ? "+" : item.kind === "expense" ? "−" : "↔";
  return `<div class="transaction"><span class="transaction-icon">${symbol}</span><div><strong>${escapeHtml(item.description)}</strong><small>${escapeHtml(item.category)} · ${item.transacted_on} · ${escapeHtml(item.payment_mode)}</small></div><strong class="amount ${item.kind}">${item.kind === "income" ? "+" : item.kind === "expense" ? "−" : ""}${currency(item.amount)}</strong><span class="row-actions"><button class="text-button" data-edit="${item.id}">Edit</button><button class="text-button" data-delete="${item.id}">Delete</button></span></div>`;
}

function renderTransactions(total) {
  $("#transaction-count").textContent =
    `${total} record${total === 1 ? "" : "s"}`;
  $("#transaction-list").innerHTML = state.transactions.length
    ? state.transactions.map(transactionRow).join("")
    : '<p class="empty">No matching transactions.</p>';
}

function renderBars(target, rows, labelKey) {
  if (!rows.length) {
    target.className = "chart empty";
    target.textContent = "No data yet.";
    return;
  }
  target.className = "chart";
  const max = Math.max(...rows.map((row) => Number(row.total)), 1);
  target.innerHTML = rows
    .map(
      (row) =>
        `<div class="bar-row"><span>${escapeHtml(row[labelKey])}</span><div class="track"><div class="bar" style="width:${(Number(row.total) / max) * 100}%"></div></div><strong>${currency(row.total)}</strong></div>`,
    )
    .join("");
}

function renderAccounts() {
  $("#account-list").innerHTML = state.accounts.length
    ? state.accounts
        .map(
          (item) =>
            `<div class="tile"><div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.kind)}</small></div><div><strong>${currency(item.balance)}</strong><button class="text-button" data-account-delete="${item.id}">Remove</button></div></div>`,
        )
        .join("")
    : '<p class="empty">No accounts.</p>';
  $("#card-list").innerHTML = state.cards.length
    ? state.cards
        .map(
          (item) =>
            `<div class="tile"><div><strong>${escapeHtml(item.name)}</strong><small>${escapeHtml(item.card_type)} · •••• ${item.last_four}</small></div><button class="text-button" data-card-delete="${item.id}">Remove</button></div>`,
        )
        .join("")
    : '<p class="empty">No cards added.</p>';
}

function renderAnalytics() {
  const data = state.summary;
  $("#analytics-count").textContent = data.count;
  $("#budget-value").textContent = currency(data.budget);
  $("#budget-used").textContent =
    `${data.budget > 0 ? Math.round((Number(data.spent) / Number(data.budget)) * 100) : 0}%`;
  renderBars($("#monthly-chart"), data.months, "month");
  renderBars($("#analytics-categories"), data.categories, "name");
}

function populateSettings() {
  const form = $("#settings-form");
  form.elements.name.value = state.user.name;
  form.elements.currency.value = state.user.currency;
  form.elements.monthly_budget.value = state.user.monthly_budget;
}

function showPage(name) {
  $$(".page").forEach((page) =>
    page.classList.toggle("active", page.id === `${name}-page`),
  );
  $$(".nav-link").forEach((link) =>
    link.classList.toggle("active", link.dataset.page === name),
  );
  $("#page-title").textContent = name[0].toUpperCase() + name.slice(1);
  $("aside").classList.remove("open");
}

function accountOptions(includeBlank = true) {
  return `${includeBlank ? '<option value="">None / cash</option>' : ""}${state.accounts.map((item) => `<option value="${item.id}">${escapeHtml(item.name)}</option>`).join("")}`;
}

function openTransaction(item = null) {
  const form = $("#transaction-form");
  form.reset();
  form.elements.category.innerHTML = categories
    .map((item) => `<option>${item}</option>`)
    .join("");
  form.elements.account_id.innerHTML = accountOptions();
  form.elements.to_account_id.innerHTML = accountOptions();
  form.elements.transacted_on.value = new Date().toISOString().slice(0, 10);
  if (item)
    Object.entries(item).forEach(([key, value]) => {
      if (form.elements[key] && value !== null)
        form.elements[key].value = value;
    });
  $("#transaction-form-title").textContent = item
    ? "Edit transaction"
    : "Add transaction";
  $("#transaction-dialog").showModal();
}

async function saveTransaction(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const data = Object.fromEntries(new FormData(form));
  const id = data.id;
  delete data.id;
  data.account_id = data.account_id ? Number(data.account_id) : null;
  data.to_account_id = data.to_account_id ? Number(data.to_account_id) : null;
  try {
    await api(id ? `/api/transactions/${id}` : "/api/transactions", {
      method: id ? "PUT" : "POST",
      body: JSON.stringify(data),
    });
    $("#transaction-dialog").close();
    await refreshAll();
    toast("Transaction saved");
  } catch (error) {
    form.querySelector(".modal-error").textContent = error.message;
  }
}

function openSimple(type) {
  const account = type === "account";
  $("#simple-title").textContent = `Add ${type}`;
  $("#simple-form").dataset.type = type;
  $("#simple-fields").innerHTML = account
    ? '<label>Name<input name="name" required></label><div class="form-row"><label>Type<select name="kind"><option>Bank</option><option>Cash</option><option>Wallet</option></select></label><label>Opening balance<input name="balance" type="number" step="0.01" value="0"></label></div>'
    : `<label>Card name<input name="name" required></label><div class="form-row"><label>Type<select name="card_type"><option>Debit</option><option>Credit</option></select></label><label>Last four digits<input name="last_four" pattern="\\d{4}" required></label></div><div class="form-row"><label>Linked account<select name="account_id">${accountOptions()}</select></label><label>Credit limit<input name="limit_amount" type="number" step="0.01" value="0"></label></div>`;
  $("#simple-dialog").showModal();
}

async function saveSimple(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const type = form.dataset.type;
  const data = Object.fromEntries(new FormData(form));
  if ("account_id" in data)
    data.account_id = data.account_id ? Number(data.account_id) : null;
  try {
    await api(`/api/${type}s`, { method: "POST", body: JSON.stringify(data) });
    $("#simple-dialog").close();
    form.reset();
    await refreshAll();
    toast(`${type} added`);
  } catch (error) {
    form.querySelector(".modal-error").textContent = error.message;
  }
}

async function handleTransactionActions(event) {
  const edit = event.target.closest("[data-edit]"),
    remove = event.target.closest("[data-delete]");
  if (edit)
    openTransaction(
      state.transactions.find((item) => item.id === Number(edit.dataset.edit)),
    );
  if (remove && confirm("Delete this transaction?")) {
    await api(`/api/transactions/${remove.dataset.delete}`, {
      method: "DELETE",
    });
    await refreshAll();
    toast("Transaction deleted");
  }
}

async function smartAdd(event) {
  event.preventDefault();
  try {
    const parsed = await api("/api/ai/parse", {
      method: "POST",
      body: JSON.stringify(
        Object.fromEntries(new FormData(event.currentTarget)),
      ),
    });
    openTransaction(parsed);
    event.currentTarget.reset();
  } catch (error) {
    toast(error.message);
  }
}

async function saveSettings(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget));
  data.onboarded = true;
  state.user = await api("/api/me", {
    method: "PUT",
    body: JSON.stringify(data),
  });
  $("#settings-message").textContent = "Preferences saved.";
  await refreshAll();
}

async function sendChat(event) {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget));
  $("#chat-messages").insertAdjacentHTML(
    "beforeend",
    `<p class="user-message">${escapeHtml(data.message)}</p>`,
  );
  event.currentTarget.reset();
  const result = await api("/api/ai/chat", {
    method: "POST",
    body: JSON.stringify(data),
  });
  $("#chat-messages").insertAdjacentHTML(
    "beforeend",
    `<p class="bot">${escapeHtml(result.answer)}</p>`,
  );
}

function logout() {
  state.token = null;
  state.user = null;
  localStorage.removeItem("finwise_token");
  showApp(false);
}

$("#auth-form").addEventListener("submit", authenticate);
$("#auth-toggle").addEventListener("click", toggleAuth);
$("#logout").addEventListener("click", async () => {
  try {
    await api("/api/auth/logout", { method: "POST" });
  } finally {
    logout();
  }
});
$$(".nav-link").forEach((link) =>
  link.addEventListener("click", () => showPage(link.dataset.page)),
);
$$("[data-go]").forEach((button) =>
  button.addEventListener("click", () => showPage(button.dataset.go)),
);
$("#menu").onclick = () => $("aside").classList.toggle("open");
$("#new-transaction").onclick = () => openTransaction();
$("#transaction-form").addEventListener("submit", saveTransaction);
$("#transaction-list").addEventListener("click", handleTransactionActions);
$("#recent-list").addEventListener("click", handleTransactionActions);
$("#quick-form").addEventListener("submit", smartAdd);
$("#add-account").onclick = () => openSimple("account");
$("#add-card").onclick = () => openSimple("card");
$("#simple-form").addEventListener("submit", saveSimple);
$("#account-list").onclick = async (event) => {
  const button = event.target.closest("[data-account-delete]");
  if (button) {
    await api(`/api/accounts/${button.dataset.accountDelete}`, {
      method: "DELETE",
    });
    await refreshAll();
  }
};
$("#card-list").onclick = async (event) => {
  const button = event.target.closest("[data-card-delete]");
  if (button) {
    await api(`/api/cards/${button.dataset.cardDelete}`, { method: "DELETE" });
    await refreshAll();
  }
};
[$("#kind-filter"), $("#category-filter")].forEach((control) =>
  control.addEventListener("change", async () => {
    const result = await api(buildTransactionUrl());
    state.transactions = result.items;
    renderTransactions(result.total);
  }),
);
let searchTimer;
$("#search").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(async () => {
    const result = await api(buildTransactionUrl());
    state.transactions = result.items;
    renderTransactions(result.total);
  }, 250);
});
$("#category-filter").innerHTML += categories
  .map((item) => `<option>${item}</option>`)
  .join("");
$("#settings-form").addEventListener("submit", saveSettings);
$("#open-chat").onclick = () => $("#chat-dialog").showModal();
$("#chat-form").addEventListener("submit", sendChat);
$$(".close-dialog").forEach((button) =>
  button.addEventListener("click", () => button.closest("dialog").close()),
);
initialize();
