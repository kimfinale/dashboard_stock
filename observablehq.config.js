export default {
  title: "Stock Investment Dashboard",
  root: "src",
  theme: "dark", // Defaulting to dark as requested "nice to have" and usually preferred for financial dashboards
  sidebar: false, // Single page dashboard, sidebar might not be needed or can be simple
  pager: false, // Single page
  // The path to the root of the application relative to the base URL.
  // For example, if the application is deployed to https://example.com/app/, the base should be "/app".
  // Use relative paths for myblog deployment, absolute for GitHub Pages
  base: process.env.BUILD_TARGET === "myblog" ? "./" : "/dashboard_stock",
};
