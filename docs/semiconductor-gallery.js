const dcStatsEl = document.getElementById("dc-stats");
const dcPostsEl = document.getElementById("dc-posts");
const dcTemplate = document.getElementById("dc-post-template");
const dcSourceLink = document.getElementById("dc-source-link");

function statCard(label, value) {
  const div = document.createElement("div");
  div.className = "stat-card";
  div.innerHTML = `<div class="stat-label">${label}</div><div class="stat-value">${value}</div>`;
  return div;
}

function makeDcCard(post) {
  const node = dcTemplate.content.firstElementChild.cloneNode(true);
  node.querySelector(".post-title").textContent = post.title;
  node.querySelector(".post-meta").textContent =
    `${post.author || "익명"} · ${post.published_at || "-"} · 조회 ${post.views} · 추천 ${post.recommends} · 댓글 ${post.comments}`;
  node.querySelector(".post-summary").textContent = post.excerpt || "본문 발췌를 불러오지 못했습니다.";
  const link = node.querySelector(".post-link");
  link.href = post.link;
  return node;
}

async function bootDcPage() {
  const response = await fetch("./data/dc_semiconductor.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("dc_semiconductor.json not found");
  }
  const data = await response.json();
  dcSourceLink.href = data.source_link;
  dcStatsEl.append(
    statCard("마지막 실행", new Date(data.generated_at).toLocaleString("ko-KR")),
    statCard("수집 글 수", `${data.total_posts}건`)
  );
  data.posts.forEach((post) => dcPostsEl.append(makeDcCard(post)));
}

bootDcPage().catch(() => {
  dcStatsEl.innerHTML = "";
  dcPostsEl.innerHTML = '<p class="empty-state">디시 데이터가 아직 없습니다. 워크플로를 한 번 실행해 주세요.</p>';
});
