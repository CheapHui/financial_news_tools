
import SignalsDashboard from "./SignalsDashboard";
export default function App() {
  return <SignalsDashboard baseUrl="" />; // 留空 → 用 Nginx 反代 /api
}