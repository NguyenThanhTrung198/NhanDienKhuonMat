import Layout from "@/components/Layout";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import {
  ShieldAlert,
  UserX,
  CheckCircle2,
  Ban,
  Search,
  AlertTriangle,
  Clock,
  Camera,
  MoreHorizontal,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const unknownDetections = [
  {
    id: 1,
    time: "10:45 AM",
    location: "Cổng chính",
    cam: "CAM-01",
    img: "https://scontent.fsgn2-7.fna.fbcdn.net/v/t39.30808-1/588633366_867680685689485_4421037800516091869_n.jpg?stp=dst-jpg_s200x200_tt6&_nc_cat=108&ccb=1-7&_nc_sid=e99d92&_nc_eui2=AeEg2iBUOclDyESaXgYHlFaUuGstiexaxBS4ay2J7FrEFL4R2jdRGx6zvX2kriu62VQWQnpGRiNgde8AMeMxgglU&_nc_ohc=WwO0CBMilzkQ7kNvwFT4sQs&_nc_oc=AdnMLJefwaLldM6RNipcrOcEtM7tna-7gikmc4Q4Glzayx2TXXiYvbNCixWnBI__0yE&_nc_zt=24&_nc_ht=scontent.fsgn2-7.fna&_nc_gid=jJsC3ZQJxR6NCBAA07iGmw&oh=00_AflUYhlntb3VO3DEH9YuKS2BvipbWvOLH57himab3QrRyQ&oe=694934C9",
  },
  {
    id: 2,
    time: "10:12 AM",
    location: "Cửa sau",
    cam: "CAM-03",
    img: "https://images.unsplash.com/photo-1590086782792-42dd2350140d?w=400&h=400&fit=crop",
  },
  {
    id: 3,
    time: "09:30 AM",
    location: "Sảnh",
    cam: "CAM-02",
    img: "https://images.unsplash.com/photo-1542909168-82c3e7fdca5c?w=400&h=400&fit=crop",
  },
];

const blacklist = [
  {
    id: "BL-001",
    name: "Thảo",
    reason: "Cố gắng đột nhập",
    date: "2023-11-15",
    status: "Active",
    img: "https://scontent.fsgn2-7.fna.fbcdn.net/v/t39.30808-1/588633366_867680685689485_4421037800516091869_n.jpg?stp=dst-jpg_s200x200_tt6&_nc_cat=108&ccb=1-7&_nc_sid=e99d92&_nc_eui2=AeEg2iBUOclDyESaXgYHlFaUuGstiexaxBS4ay2J7FrEFL4R2jdRGx6zvX2kriu62VQWQnpGRiNgde8AMeMxgglU&_nc_ohc=WwO0CBMilzkQ7kNvwFT4sQs&_nc_oc=AdnMLJefwaLldM6RNipcrOcEtM7tna-7gikmc4Q4Glzayx2TXXiYvbNCixWnBI__0yE&_nc_zt=24&_nc_ht=scontent.fsgn2-7.fna&_nc_gid=jJsC3ZQJxR6NCBAA07iGmw&oh=00_AflUYhlntb3VO3DEH9YuKS2BvipbWvOLH57himab3QrRyQ&oe=694934C9p",
  },
  {
    id: "BL-002",
    name: "Nam",
    reason: "Cựu nhân viên - Rủi ro an ninh",
    date: "2023-10-20",
    status: "Active",
    img: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=400&fit=crop",
  },
];

export default function Security() {
  return (
    <Layout>
      <div className="flex flex-col gap-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">
              An ninh & Cảnh báo
            </h2>
            <p className="text-muted-foreground">
              Quản lý mối đe dọa, phát hiện người lạ và danh sách đen
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="destructive">
              <ShieldAlert className="mr-2 h-4 w-4" />
              Báo cáo Sự cố
            </Button>
          </div>
        </div>

        <Tabs defaultValue="unknown" className="w-full">
          <TabsList className="grid w-full max-w-md grid-cols-2">
            <TabsTrigger value="unknown">Phát hiện người lạ</TabsTrigger>
            <TabsTrigger value="blacklist">
              Cơ sở dữ liệu danh sách đen
            </TabsTrigger>
          </TabsList>

          <TabsContent value="unknown" className="mt-6">
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {unknownDetections.map((item) => (
                <Card
                  key={item.id}
                  className="overflow-hidden border-l-4 border-l-amber-500"
                >
                  <div className="aspect-video w-full bg-muted relative">
                    <img
                      src={item.img}
                      alt="Detection"
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-2 right-2 bg-black/60 text-white text-xs px-2 py-1 rounded font-mono flex items-center gap-1">
                      <Camera className="h-3 w-3" />
                      {item.cam}
                    </div>
                    <div className="absolute bottom-2 left-2 bg-amber-500/90 text-white text-xs px-2 py-1 rounded font-bold flex items-center gap-1">
                      <AlertTriangle className="h-3 w-3" />
                      KHÔNG XÁC ĐỊNH
                    </div>
                  </div>
                  <CardContent className="p-4">
                    <div className="flex justify-between items-start mb-4">
                      <div>
                        <div className="font-medium text-lg">
                          {item.location}
                        </div>
                        <div className="text-sm text-muted-foreground flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {item.time}
                        </div>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button className="flex-1" variant="outline" size="sm">
                        <UserX className="mr-2 h-4 w-4" />
                        Danh sách đen
                      </Button>
                      <Button className="flex-1" size="sm">
                        <CheckCircle2 className="mr-2 h-4 w-4" />
                        Đăng ký
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
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

            <div className="grid gap-4">
              {blacklist.map((item) => (
                <Card
                  key={item.id}
                  className="flex flex-col sm:flex-row items-center p-4 gap-4"
                >
                  <Avatar className="h-16 w-16 border-2 border-destructive">
                    <AvatarImage src={item.img} />
                    <AvatarFallback>BL</AvatarFallback>
                  </Avatar>
                  <div className="flex-1 text-center sm:text-left">
                    <div className="flex items-center justify-center sm:justify-start gap-2">
                      <h3 className="font-bold text-lg">{item.name}</h3>
                      <Badge variant="destructive">{item.status}</Badge>
                    </div>
                    <p className="text-sm text-muted-foreground font-mono">
                      {item.id}
                    </p>
                    <div className="mt-1 text-sm bg-destructive/10 text-destructive inline-block px-2 py-0.5 rounded">
                      Lý do: {item.reason}
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1 text-sm text-muted-foreground">
                    <div>Đã thêm: {item.date}</div>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem>Xem bằng chứng</DropdownMenuItem>
                        <DropdownMenuItem>Sửa chi tiết</DropdownMenuItem>
                        <DropdownMenuItem className="text-emerald-500">
                          Xóa khỏi danh sách đen
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </Card>
              ))}
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}
