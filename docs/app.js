const statsEl = document.getElementById("stats");
const priorityPostsEl = document.getElementById("priority-posts");
const allPostsEl = document.getElementById("all-posts");
const filtersEl = document.getElementById("filters");
const priorityCountEl = document.getElementById("priority-count");
const searchInputEl = document.getElementById("search-input");
const template = document.getElementById("post-template");

let currentClassification = "전체";
let allPosts = [];

function statCard(label, value) {
  const div = document.createElement("div");
  div.className = "stat-card";
  div.innerHTML = `<div class="stat-label">${label}</div><div class="stat-value">${value}</div>`;
  return div;
}

function renderStats(data) {
  statsEl.innerHTML = "";
  statsEl.append(
    statCard("마지막 실행", new Date(data.generated_at).toLocaleString("ko-KR")),
    statCard("총 새 글", `${data.total_posts}건`),
    statCard("우선 블로거", `${data.priority_post_count}건`),
    statCard("분류 수", `${Object.keys(data.classification_counts).length}개`)
  );
}

function createFilterButton(label) {
  const button = document.createElement("button");
  button.className = `filter-btn${label === currentClassification ? " active" : ""}`;
  button.textContent = label;
  button.addEventListener("click", () => {
    currentClassification = label;
    renderFilters();
    renderAllPosts();
  });
  return button;
}

function renderFilters() {
  const classifications = ["전체", ...new Set(allPosts.map((post) => post.classification || "미분류"))];
  filtersEl.innerHTML = "";
  classifications.forEach((label) => filtersEl.append(createFilterButton(label)));
}

function makePostCard(post) {
  const node = template.content.firstElementChild.cloneNode(true);
  node.querySelector(".chip-classification").textContent = post.classification || "미분류";
  node.querySelector(".chip-priority").style.display = post.is_priority ? "inline-flex" : "none";
  node.querySelector(".post-title").textContent = post.title;
  node.querySelector(".post-meta").textContent =
    `${post.display_name} · ${new Date(post.published_at).toLocaleString("ko-KR")}`;
  node.querySelector(".post-summary").textContent = post.summary;
  const link = node.querySelector(".post-link");
  link.href = post.link;
  return node;
}

function renderPriorityPosts() {
  const priorityPosts = allPosts.filter((post) => post.is_priority);
  priorityCountEl.textContent = `${priorityPosts.length}건`;
  priorityPostsEl.innerHTML = "";
  if (!priorityPosts.length) {
    priorityPostsEl.innerHTML = '<p class="empty-state">이번 실행에서는 우선 블로거 새 글이 없습니다.</p>';
    return;
  }
  priorityPosts.forEach((post) => priorityPostsEl.append(makePostCard(post)));
}

function renderAllPosts() {
  const query = searchInputEl.value.trim().toLowerCase();
  const filtered = allPosts.filter((post) => {
    const hitClassification = currentClassification === "전체" || (post.classification || "미분류") === currentClassification;
    const haystack = [post.title, post.display_name, post.blog_title, post.classification, post.summary]
      .join(" ")
      .toLowerCase();
    return hitClassification && (!query || haystack.includes(query));
  });

  allPostsEl.innerHTML = "";
  if (!filtered.length) {
    allPostsEl.innerHTML = '<p class="empty-state">조건에 맞는 글이 없습니다.</p>';
    return;
  }
  filtered.forEach((post) => allPostsEl.append(makePostCard(post)));
}

async function boot() {
  const response = await fetch("./data/latest.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("latest.json not found");
  }
  const data = await response.json();
  allPosts = data.posts;
  renderStats(data);
  renderPriorityPosts();
  renderFilters();
  renderAllPosts();
}

searchInputEl.addEventListener("input", renderAllPosts);

boot().catch(() => {
  statsEl.innerHTML = "";
  priorityPostsEl.innerHTML = '<p class="empty-state">대시보드 데이터가 아직 없습니다. 워크플로를 한 번 실행해 주세요.</p>';
  allPostsEl.innerHTML = "";
});
