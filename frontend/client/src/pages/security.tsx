import React, { useState, useEffect } from "react";
import Layout from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  ShieldAlert,
  UserX,
  CheckCircle2,
  Search,
  AlertTriangle,
  Clock,
  Camera,
  MoreHorizontal,
  RefreshCw,
  Eye,
  MapPin,
  List,
  ImageIcon,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function Security() {
  const [unknownDetections, setUnknownDetections] = useState([]);
  const [blacklist, setBlacklist] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedAlert, setSelectedAlert] = useState(null);

  // [FIX] HÀM XỬ LÝ ĐƯỜNG DẪN ẢNH CHUẨN XÁC
  const getImageUrl = (path: any) => {
    // 1. Kiểm tra nếu path rỗng hoặc null hoặc không phải chuỗi
    if (!path || typeof path !== "string" || path.trim() === "") {
      return "https://placehold.co/600x400?text=No+Image";
    }

    // 2. Nếu là ảnh online (http...) -> Giữ nguyên
    if (path.startsWith("http")) return path;

    // 3. Chuẩn hóa đường dẫn nội bộ:
    let cleanPath = path;

    // Thay thế tất cả dấu gạch chéo ngược '\' thành '/' (quan trọng cho Windows)
    cleanPath = cleanPath.replace(/\\/g, "/");

    // Loại bỏ dấu chấm ở đầu (ví dụ ./static -> /static)
    if (cleanPath.startsWith(".")) {
      cleanPath = cleanPath.substring(1);
    }

    // Đảm bảo luôn bắt đầu bằng dấu /
    if (!cleanPath.startsWith("/")) {
      cleanPath = "/" + cleanPath;
    }

    // Kết quả mong đợi: http://localhost:5000/static/strangers/ten_anh.jpg
    return `http://localhost:5000${cleanPath}`;
  };

  const fetchAlerts = async () => {
    try {
      setLoading(true);
      const response = await fetch("http://localhost:5000/api/security/alerts");
      const data = await response.json();
      setUnknownDetections(data);
    } catch (error) {
      console.error("Lỗi tải dữ liệu cảnh báo:", error);
    } finally {
      setLoading(false);
    }
  };

  const fetchBlacklist = async () => {
    try {
      const response = await fetch(
        "http://localhost:5000/api/security/blacklist"
      );
      const data = await response.json();
      setBlacklist(data);
    } catch (error) {
      console.error("Lỗi tải blacklist:", error);
    }
  };

  const handleAddToBlacklist = async () => {
    if (!selectedAlert) return;
    try {
      const response = await fetch(
        "http://localhost:5000/api/security/blacklist/add",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            name: `Đối tượng ${selectedAlert.location}`,
            reason: `Phát hiện tại ${selectedAlert.cam} lúc ${selectedAlert.time}`,
            image: selectedAlert.img,
          }),
        }
      );
      const result = await response.json();
      if (result.success) {
        alert("Đã thêm vào danh sách đen thành công!");
        setSelectedAlert(null);
        fetchBlacklist();
        fetchAlerts();
      } else {
        alert("Lỗi: " + result.message);
      }
    } catch (error) {
      alert("Có lỗi xảy ra khi kết nối server.");
    }
  };

  useEffect(() => {
    fetchAlerts();
    fetchBlacklist();
    const interval = setInterval(() => {
      fetchAlerts();
      fetchBlacklist();
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  // Component hiển thị thẻ Card (Dùng chung cho cả 2 tab)
  const PersonCard = ({
    item,
    isBlacklist = false,
  }: {
    item: any;
    isBlacklist?: boolean;
  }) => (
    <Card
      key={item.id}
      className={`overflow-hidden border-l-4 shadow-md hover:shadow-lg transition-all ${
        isBlacklist ? "border-l-red-600 bg-red-50/50" : "border-l-amber-500"
      }`}
    >
      <div
        className="aspect-video w-full bg-muted relative group cursor-pointer"
        onClick={() => setSelectedAlert(item)}
      >
        <img
          src={`${getImageUrl(item.img)}?t=${Date.now()}`}
          alt="Detection"
          className="w-full h-full object-cover transition-transform group-hover:scale-105"
          onError={(e) => {
            (e.target as HTMLImageElement).src =
              "https://placehold.co/600x400?text=Image+Error";
          }}
        />

        <div className="absolute top-2 right-2 bg-black/60 text-white text-xs px-2 py-1 rounded font-mono flex items-center gap-1">
          {isBlacklist ? (
            <span className="font-bold">ID: BL-{item.id}</span>
          ) : (
            <>
              <Camera className="h-3 w-3" /> {item.cam}
            </>
          )}
        </div>

        {item.count > 1 ? (
          <div className="absolute top-2 left-2 bg-red-600 text-white text-xs px-2 py-1 rounded-full font-bold flex items-center gap-1 animate-pulse">
            <Eye className="h-3 w-3" /> Xuất hiện: {item.count} lần
          </div>
        ) : (
          <div
            className={`absolute bottom-2 left-2 text-white text-xs px-2 py-1 rounded font-bold flex items-center gap-1 ${
              isBlacklist ? "bg-red-600" : "bg-amber-500/90"
            }`}
          >
            <AlertTriangle className="h-3 w-3" />{" "}
            {isBlacklist ? "ĐỐI TƯỢNG NGUY HIỂM" : "KHÔNG XÁC ĐỊNH"}
          </div>
        )}

        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-all flex items-center justify-center opacity-0 group-hover:opacity-100">
          <span className="bg-white/90 text-black px-3 py-1 rounded-full text-sm font-medium">
            Xem lịch sử
          </span>
        </div>
      </div>
      <CardContent className="p-4">
        <div className="flex justify-between items-start mb-4">
          <div>
            <div className="font-bold text-lg text-red-700">
              {item.name || item.location}
            </div>
            <div className="text-sm text-muted-foreground flex items-center gap-1">
              <Clock className="h-3 w-3" /> {item.date} -{" "}
              {item.time ? item.time : "N/A"}
            </div>
            {isBlacklist && (
              <div className="text-xs mt-1 text-red-500 italic truncate max-w-[200px]">
                Lý do: {item.reason}
              </div>
            )}
          </div>
        </div>

        {!isBlacklist && (
          <div className="flex gap-2">
            <Button
              className="w-full bg-red-600 hover:bg-red-700 text-white"
              size="sm"
              onClick={(e) => {
                e.stopPropagation();
                setSelectedAlert(item);
                handleAddToBlacklist();
              }}
            >
              <UserX className="mr-2 h-4 w-4" /> Thêm vào Blacklist
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );

  return (
    <Layout>
      <div className="flex flex-col gap-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">
              An ninh & Cảnh báo
            </h2>
            <p className="text-muted-foreground">
              Quản lý mối đe dọa và phát hiện người lạ (Cập nhật Real-time)
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              onClick={() => {
                fetchAlerts();
                fetchBlacklist();
              }}
              disabled={loading}
            >
              <RefreshCw
                className={`mr-2 h-4 w-4 ${loading ? "animate-spin" : ""}`}
              />{" "}
              Làm mới
            </Button>
            <Button variant="destructive">
              <ShieldAlert className="mr-2 h-4 w-4" /> Báo cáo Sự cố
            </Button>
          </div>
        </div>

        <Tabs defaultValue="unknown" className="w-full">
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="unknown">
              Phát hiện người lạ ({unknownDetections.length})
            </TabsTrigger>
            <TabsTrigger value="blacklist">
              Danh sách đen ({blacklist.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="unknown" className="mt-6">
            {unknownDetections.length === 0 ? (
              <div className="text-center py-10 text-muted-foreground">
                Chưa phát hiện người lạ nào.
              </div>
            ) : (
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {unknownDetections.map((item: any) => (
                  <PersonCard key={item.id} item={item} isBlacklist={false} />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="blacklist" className="mt-6 space-y-6">
            <div className="flex items-center gap-2">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Tìm kiếm danh sách đen..."
                  className="pl-9"
                />
              </div>
            </div>
            {blacklist.length === 0 ? (
              <div className="text-center py-10 text-muted-foreground">
                Danh sách đen trống.
              </div>
            ) : (
              <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                {blacklist.map((item: any) => (
                  <PersonCard key={item.id} item={item} isBlacklist={true} />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>

      <Dialog
        open={!!selectedAlert}
        onOpenChange={(open) => !open && setSelectedAlert(null)}
      >
        <DialogContent className="sm:max-w-xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-xl text-red-600">
              <ShieldAlert className="h-6 w-6" /> CHI TIẾT HOẠT ĐỘNG
            </DialogTitle>
            <DialogDescription>
              Đối tượng:{" "}
              <span className="font-bold">
                {selectedAlert?.name || selectedAlert?.location}
              </span>{" "}
              đã xuất hiện{" "}
              <span className="font-bold text-red-600">
                {selectedAlert?.count} lần
              </span>
              .
            </DialogDescription>
          </DialogHeader>

          {selectedAlert && (
            <div className="grid gap-6 py-2">
              <div className="space-y-4">
                <div className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
                  <ImageIcon className="h-4 w-4" /> LỊCH SỬ GHI NHẬN (Mới nhất
                  &rarr; Cũ nhất)
                </div>

                {(selectedAlert.details || []).map(
                  (detail: any, index: number) => (
                    <div
                      key={index}
                      className="flex gap-4 p-3 border rounded-lg bg-muted/20 items-center hover:bg-muted/50 transition-colors"
                    >
                      <div className="relative w-24 h-24 flex-shrink-0 rounded-md overflow-hidden border bg-black">
                        <img
                          src={getImageUrl(detail.img)}
                          alt={`Lần xuất hiện ${index}`}
                          className="w-full h-full object-contain"
                          onError={(e) => {
                            (e.target as HTMLImageElement).src =
                              "https://placehold.co/100?text=Error";
                          }}
                        />
                      </div>
                      <div className="flex-1 flex flex-col justify-center gap-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-base text-red-600">
                            Ghi nhận lần {selectedAlert.count - index}
                          </span>
                          <Badge
                            variant="outline"
                            className="font-mono bg-white text-black"
                          >
                            {detail.time}
                          </Badge>
                        </div>
                        <div className="text-sm text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" /> Ngày:{" "}
                          {(selectedAlert as any).date}
                        </div>
                        <div className="text-sm text-muted-foreground flex items-center gap-1">
                          <MapPin className="h-3 w-3" /> Vị trí:{" "}
                          {(selectedAlert as any).cam}
                        </div>
                      </div>
                    </div>
                  )
                )}
              </div>

              {!selectedAlert.status?.includes("Dangerous") && (
                <div className="flex flex-col gap-2 mt-2">
                  <Button
                    className="w-full bg-red-600 hover:bg-red-700 text-white py-6 text-lg font-bold shadow-md hover:shadow-lg transition-all"
                    onClick={handleAddToBlacklist}
                  >
                    <UserX className="mr-2 h-6 w-6" /> THÊM VÀO DANH SÁCH ĐEN
                    NGAY
                  </Button>

                  <Button
                    variant="ghost"
                    className="w-full text-muted-foreground hover:text-black"
                    onClick={() => setSelectedAlert(null)}
                  >
                    Bỏ qua, đóng cửa sổ này
                  </Button>
                </div>
              )}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Layout>
  );
}
