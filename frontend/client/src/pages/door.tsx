import Layout from "@/components/Layout";
import CameraFeed from "@/components/CameraFeed";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DoorOpen,
  DoorClosed,
  Camera,
  ScanFace,
  Power,
  Zap,
  Shield,
  Timer,
} from "lucide-react";
import { useState } from "react";

type DoorMode = "AUTO" | "MANUAL" | "LOCKDOWN";
type SecurityLevel = "SAFE" | "WARNING" | "DANGER";

type Door = {
  id: string;
  name: string;
  cameraId: number;
  enabled: boolean;
  status: "OPEN" | "CLOSED";
  mode: DoorMode;
  security: SecurityLevel;
  lastUser: string | null;
  openedSeconds: number;
};

const initialDoors: Door[] = [
  {
    id: "MAIN",
    name: "Cửa chính",
    cameraId: 0,
    enabled: true,
    status: "OPEN",
    mode: "Tự Động",
    security: "Bình Thường",
    lastUser: "Nguyễn Thành Trung",
    openedSeconds: 42,
  },
  {
    id: "SIDE",
    name: "Cửa phụ",
    cameraId: 1,
    enabled: false,
    status: "CLOSED",
    mode: "Khóa",
    security: "Bình Thường",
    lastUser: null,
    openedSeconds: 0,
  },
];

export default function DoorMonitor() {
  const [doors, setDoors] = useState<Door[]>(initialDoors);

  const toggleDoor = (id: string) => {
    setDoors((prev) =>
      prev.map((d) => (d.id === id ? { ...d, enabled: !d.enabled } : d))
    );
  };

  const formatTime = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(
      2,
      "0"
    )}`;

  const securityColor = (level: SecurityLevel) => {
    if (level === "SAFE") return "bg-emerald-500/10 text-emerald-500";
    if (level === "WARNING") return "bg-yellow-500/10 text-yellow-500";
    return "bg-muted text-muted-foreground";
  };

  return (
    <Layout>
      <div className="flex flex-col gap-8">
        {/* HEADER */}
        <div>
          <h2 className="text-3xl font-bold"> Giám sát cửa ra vào</h2>
        </div>

        {/* CAMERA GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {doors.map((door) => (
            <Card key={door.id}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Camera className="h-5 w-5 text-primary" />
                  {door.name}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <CameraFeed
                  useWebcam
                  camId={door.cameraId}
                  label={`CAM-${door.id}`}
                  location={door.name}
                />

                <div className="flex justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <ScanFace className="h-4 w-4 text-primary" />
                    {door.lastUser ? (
                      <span>
                        AI: <b className="text-primary">{door.lastUser}</b>
                      </span>
                    ) : (
                      <span className="text-muted-foreground">
                        Chưa nhận diện
                      </span>
                    )}
                  </div>

                  <Badge
                    className={
                      door.status === "OPEN"
                        ? "bg-emerald-500/10 text-emerald-500"
                        : "bg-muted text-muted-foreground"
                    }
                  >
                    {door.status}
                  </Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* DOOR CONTROL */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {doors.map((door) => (
            <Card key={door.id}>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  {door.status === "OPEN" ? (
                    <DoorOpen className="text-emerald-500" />
                  ) : (
                    <DoorClosed />
                  )}
                  {door.name}
                </CardTitle>
              </CardHeader>

              <CardContent className="space-y-4 text-sm">
                {/* ENABLE */}
                <div className="flex justify-between items-center">
                  <span>Kích hoạt cửa</span>
                  <Switch
                    checked={door.enabled}
                    onCheckedChange={() => toggleDoor(door.id)}
                  />
                </div>

                {/* MODE */}
                <div className="flex justify-between items-center">
                  <span>Chế độ</span>
                  <Badge variant="outline">{door.mode}</Badge>
                </div>

                {/* SECURITY */}
                <div className="flex justify-between items-center">
                  <span>An ninh</span>
                  <Badge className={securityColor(door.security)}>
                    <Shield className="h-3 w-3 mr-1" />
                    {door.security}
                  </Badge>
                </div>
                {/* TIMER */}
                <div className="flex justify-between items-center">
                  <span>Thời gian mở</span>
                  <span className="font-mono flex items-center gap-1 text-muted-foreground">
                    <Timer className="h-4 w-4" />
                    {door.status === "OPEN"
                      ? formatTime(door.openedSeconds)
                      : "--:--"}
                  </span>
                </div>

                {/* ACTION */}
                <div className="flex gap-2 pt-2">
                  <Button
                    variant="outline"
                    disabled={!door.enabled}
                    className="flex-1"
                  >
                    <Zap className="h-4 w-4 mr-2" />
                    Test Relay
                  </Button>

                  <Button
                    variant="secondary"
                    disabled={!door.enabled}
                    className="flex-1"
                  >
                    <Power className="h-4 w-4 mr-2" />
                    Mở thử
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </Layout>
  );
}
