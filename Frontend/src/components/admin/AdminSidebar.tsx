"use client";

import * as React from "react";
import Link from "next/link";
import {
  IconBuilding,
  IconUsers,
  IconChartBar,
  IconSettings,
  IconDashboard,
  IconMail,
  IconShield,
  IconUserPlus,
  IconBriefcase,
} from "@tabler/icons-react";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";

const adminNavItems = [
  {
    title: "Dashboard",
    url: "/admin",
    icon: IconDashboard,
  },
  {
    title: "Organizations",
    url: "/admin/organizations",
    icon: IconBuilding,
  },
  {
    title: "Invite Organization",
    url: "/admin/organizations/invite",
    icon: IconMail,
  },
  {
    title: "Members",
    url: "/admin/members",
    icon: IconUsers,
  },
  {
    title: "Analytics",
    url: "/admin/analytics",
    icon: IconChartBar,
  },
  {
    title: "Venture Builders",
    url: "/admin/venture-builders",
    icon: IconBriefcase,
  },
];

export function AdminSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const pathname = usePathname();

  return (
    <Sidebar collapsible="offcanvas" {...props}>
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              asChild
              className="data-[slot=sidebar-menu-button]:!p-1.5"
            >
              <Link href="/admin">
                <IconShield className="!size-5" />
                <span className="text-base font-semibold">Yuba Admin</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>
      <SidebarContent>
        <SidebarMenu>
          {adminNavItems.map((item) => (
            <SidebarMenuItem key={item.title}>
              <SidebarMenuButton
                asChild
                isActive={pathname === item.url}
              >
                <Link href={item.url}>
                  <item.icon />
                  <span>{item.title}</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild>
              <Link href="/">
                <IconUsers />
                <span>Back to User Portal</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
    </Sidebar>
  );
}
