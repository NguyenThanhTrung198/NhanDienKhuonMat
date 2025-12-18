import { useState, useEffect } from "react";
import Layout from "@/components/Layout";
import StatusCard from "@/components/StatusCard";
import CameraFeed from "@/components/CameraFeed";
import { Users, DoorClosed, AlertTriangle, Activity } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

// Dữ liệu mẫu ban đầu cho biểu đồ
const initialChartData = [
  { time: "10:00:00", visits: 45 },
  { time: "10:00:05", visits: 52 },
  { time: "10:00:10", visits: 38 },
  { time: "10:00:15", visits: 65 },
  { time: "10:00:20", visits: 48 },
  { time: "10:00:25", visits: 60 },
  { time: "10:00:30", visits: 55 },
];

const sampleNames = [
  "Nguyễn Văn An",
  "Trần Thị Mai",
  "Lê Hoàng Nam",
  "Phạm Văn Hùng",
  "Vũ Thị Lan",
  "Hoàng Tuấn Kiệt",
  "Unknown User",
];
const sampleLocs = [
  "Cổng Chính (FaceID)",
  "Thang máy B",
  "Cửa thoát hiểm",
  "Phòng Server",
  "Sảnh Lễ Tân",
];

export default function Dashboard() {
  const [chartData, setChartData] = useState(initialChartData);

  // State Logs
  const [logs, setLogs] = useState([
    {
      id: "NV-2301",
      name: "Nguyễn Văn An",
      loc: "Cổng Chính (FaceID)",
      time: "12:10:45",
      status: "Hợp lệ",
    },
    {
      id: "KH-0012",
      name: "Trần Thị Mai",
      loc: "Thang máy B",
      time: "12:08:30",
      status: "Hợp lệ",
    },
    {
      id: "UNKNOWN",
      name: "Không xác định",
      loc: "Cửa thoát hiểm",
      time: "11:55:12",
      status: "Cảnh báo",
    },
  ]);

  const [gpuLoad, setGpuLoad] = useState(0); // GPU cũng nên start từ 0 cho đồng bộ
  const [temp, setTemp] = useState(40);

  // --- SỬA Ở ĐÂY: Mặc định là 0 ---
  const [presentCount, setPresentCount] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      const now = new Date();
      const timeString = now.toLocaleTimeString("vi-VN", { hour12: false });

      // A. Cập nhật biểu đồ
      setChartData((prevData) => {
        const newVisits = Math.floor(Math.random() * (80 - 30 + 1) + 30);
        const newData = [
          ...prevData.slice(1),
          { time: timeString, visits: newVisits },
        ];
        return newData;
      });

      // B. Cập nhật chỉ số hệ thống (Nhảy số)
      setGpuLoad(
        (prev) =>
          Math.min(100, Math.max(10, prev + Math.floor(Math.random() * 20 - 5))) // Tăng tốc độ biến động lúc đầu
      );
      setTemp((prev) =>
        Math.min(90, Math.max(40, prev + Math.floor(Math.random() * 4 - 2)))
      );

      // --- C. LOGIC MỚI CHO NHÂN SỰ ---
      setPresentCount((prev) => {
        const targetMin = 135;
        const targetMax = 150;

        // Giai đoạn 1: Nếu chưa đạt mức tối thiểu (đang khởi động)
        if (prev < targetMin) {
          // Tăng nhanh (cộng thêm từ 10 đến 25 người mỗi lần quét)
          // Để tạo cảm giác dữ liệu đang load vào vù vù
          const jump = Math.floor(Math.random() * 15) + 10;
          return Math.min(targetMax, prev + jump);
        }

        // Giai đoạn 2: Đã ổn định (logic cũ)
        // 70% giữ nguyên, 30% thay đổi nhẹ (+/- 1)
        if (Math.random() > 0.3) return prev;
        const change = Math.random() > 0.5 ? 1 : -1;
        return Math.min(targetMax, Math.max(targetMin, prev + change));
      });

      // D. Random Logs
      if (Math.random() > 0.7) {
        const randomName =
          sampleNames[Math.floor(Math.random() * sampleNames.length)];
        const randomLoc =
          sampleLocs[Math.floor(Math.random() * sampleLocs.length)];
        const isWarning = randomName === "Unknown User";

        const newLog = {
          id: isWarning
            ? "ALERT"
            : `NV-${Math.floor(Math.random() * 8999 + 1000)}`,
          name: randomName,
          loc: randomLoc,
          time: timeString,
          status: isWarning ? "Cảnh báo" : "Hợp lệ",
        };

        setLogs((prevLogs) => [newLog, ...prevLogs].slice(0, 5));
      }
    }, 1000); // --- Tăng tốc độ cập nhật lên 1 giây (thay vì 2s) để số nhảy từ 0 lên nhanh hơn ---

    return () => clearInterval(interval);
  }, []);

  return (
    <Layout>
      <div className="flex flex-col gap-8">
        <div className="flex items-center justify-between">
          <h2 className="text-3xl font-bold tracking-tight">
            Trung tâm Giám sát AI
          </h2>
          <div className="flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
            </span>
            <span className="text-sm text-muted-foreground font-mono">
              SYSTEM ONLINE
            </span>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StatusCard
            title="Nhân sự hiện diện"
            value={`${presentCount}/150`}
            icon={Users}
            description="Tỷ lệ đi làm hôm nay"
            // Nếu đang < 50 người (lúc mới load) thì hiện màu đỏ/vàng, đủ người thì xanh
            trend={presentCount >= 135 ? "up" : "neutral"}
            trendValue={`${((presentCount / 150) * 100).toFixed(1)}%`}
          />
          <StatusCard
            title="Cảnh báo khuôn mặt"
            value="1"
            icon={AlertTriangle}
            description="Phát hiện người lạ"
            alert={true}
          />
          <StatusCard
            title="Trạng thái Cửa từ"
            value="Đã khóa"
            icon={DoorClosed}
            description="Khu vực Server & Kho"
            trend="neutral"
            trendValue="An toàn"
          />
          <StatusCard
            title="Tải GPU xử lý"
            value={`${gpuLoad}%`}
            icon={Activity}
            description={`Nhiệt độ: ${temp}°C`}
            trend={gpuLoad > 80 ? "down" : "neutral"}
            trendValue="Real-time"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
          {/* Attendance Chart */}
          <Card className="col-span-4">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Lưu lượng theo thời gian thực</span>
                <Badge
                  variant="outline"
                  className="font-mono font-normal animate-pulse text-emerald-500 border-emerald-500"
                >
                  LIVE UPDATING
                </Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="pl-2">
              <div className="h-[300px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient
                        id="colorVisits"
                        x1="0"
                        y1="0"
                        x2="0"
                        y2="1"
                      >
                        <stop
                          offset="5%"
                          stopColor="hsl(var(--primary))"
                          stopOpacity={0.3}
                        />
                        <stop
                          offset="95%"
                          stopColor="hsl(var(--primary))"
                          stopOpacity={0}
                        />
                      </linearGradient>
                    </defs>
                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="hsl(var(--border))"
                      vertical={false}
                    />
                    <XAxis
                      dataKey="time"
                      stroke="hsl(var(--muted-foreground))"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                    />
                    <YAxis
                      stroke="hsl(var(--muted-foreground))"
                      fontSize={12}
                      tickLine={false}
                      axisLine={false}
                      tickFormatter={(value) => `${value}`}
                      domain={[0, 100]}
                    />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "hsl(var(--card))",
                        borderColor: "hsl(var(--border))",
                        borderRadius: "6px",
                        color: "hsl(var(--foreground))",
                      }}
                      itemStyle={{ color: "hsl(var(--primary))" }}
                    />
                    <Area
                      type="monotone"
                      dataKey="visits"
                      stroke="hsl(var(--primary))"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#colorVisits)"
                      isAnimationActive={true}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </CardContent>
          </Card>

          {/* Live Feeds */}
          <div className="col-span-3 space-y-4">
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-sm text-muted-foreground">
                Camera AI (Real-time)
              </h3>
              <Button
                variant="link"
                size="sm"
                className="h-auto p-0 text-primary"
              >
                Cấu hình
              </Button>
            </div>
            <div className="grid gap-4">
              <div className="grid gap-4">
                <CameraFeed
                  useWebcam={true}
                  camId={0}
                  label="CAM-01: Cổng Soát Vé"
                  location="Sảnh Chính - Tầng G"
                />

                <CameraFeed
                  useWebcam={false}
                  src="/assets/generated_images/cctv_server_room.png"
                  label="CAM-02: Phòng Server"
                  location="Khu vực hạn chế"
                  status="live"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Recent Logs Table */}
        <Card>
          <CardHeader>
            <CardTitle>Nhật ký nhận diện (Live Feed)</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {logs.map((log, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between border-b pb-4 last:border-0 last:pb-0 animate-in slide-in-from-left-2 duration-300"
                >
                  <div className="flex items-center gap-4">
                    <div className="h-9 w-9 rounded-full bg-muted flex items-center justify-center">
                      <Users className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div className="space-y-1">
                      <p className="text-sm font-medium leading-none">
                        {log.name}{" "}
                        <span className="text-xs text-muted-foreground">
                          ({log.id})
                        </span>
                      </p>
                      <p className="text-xs text-muted-foreground">{log.loc}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <Badge
                      variant="outline"
                      className={
                        log.status === "Cảnh báo"
                          ? "bg-red-500/10 text-red-500 border-red-500/20"
                          : "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
                      }
                    >
                      {log.status}
                    </Badge>
                    <span className="text-xs text-muted-foreground font-mono">
                      {log.time}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
}
