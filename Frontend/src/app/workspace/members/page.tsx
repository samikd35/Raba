"use client";

import React, { useEffect, useMemo, useRef, useState, useCallback } from "react";
import { useTeamStore } from "@/stores/teamStore";
import { useAuthStore } from "@/stores/authStore";
import { TeamService } from "@/lib/api/teamService";
import { TeamMember } from "@/types/team";
import { 
  Users, 
  Mail,
  Shield,
  Crown,
  AlertCircle,
  Loader2,
  Search,
  Filter,
  Calendar,
  BadgeCheck,
  MoreVertical
} from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { toast, Toaster } from "react-hot-toast";
import router from "next/router";

export default function TeamWorkspaceMembers() {
  const { currentTeam } = useTeamStore();
  const { user } = useAuthStore();
  const [members, setMembers] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [roleFilter, setRoleFilter] = useState<string>("all");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [sortKey, setSortKey] = useState<"name" | "email" | "role" | "joined" | "status">("name");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const abortRef = useRef<AbortController | null>(null);

  const canManageMembers = useMemo(() => {
    const role = (currentTeam as any)?.user_role || (currentTeam as any)?.role;
    return ["owner", "admin", "team_leader"].includes(String(role || "").toLowerCase());
  }, [currentTeam]);

  useEffect(() => {
    const fetchMembers = async () => {
      if (!currentTeam?.id) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);
        if (abortRef.current) {
          try { abortRef.current.abort(); } catch {}
        }
        const controller = new AbortController();
        abortRef.current = controller;
        const data = await TeamService.getTeamMembers(currentTeam.id, controller.signal as any);
        setMembers(data);
      } catch (err) {
        if ((err as any)?.name === 'AbortError') return;
        if (process.env.NODE_ENV === 'development') {
          console.error('Error fetching team members:', err);
        }
        setError(err instanceof Error ? err.message : 'Failed to load team members');
      } finally {
        setLoading(false);
      }
    };

    fetchMembers();
    return () => {
      if (abortRef.current) {
        try { abortRef.current.abort(); } catch {}
        abortRef.current = null;
      }
    };
  }, [currentTeam?.id]);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedSearch(searchTerm.trim()), 250);
    return () => clearTimeout(t);
  }, [searchTerm]);

  const getRoleVariant = (role: string) => {
    switch (role.toLowerCase()) {
      case 'team_leader':
      case 'owner':
        return 'default';
      case 'admin':
        return 'secondary';
      case 'member':
        return 'outline';
      default:
        return 'outline';
    }
  };

  const getRoleColor = (role: string) => {
    switch (role.toLowerCase()) {
      case 'owner':
        return 'bg-brand-100 text-brand-800 border-brand-200 hover:bg-brand-100';
      case 'team_leader':
        return 'bg-amber-100 text-amber-800 border-amber-200 hover:bg-amber-100';
      case 'admin':
        return 'bg-blue-100 text-blue-800 border-blue-200 hover:bg-blue-100';
      case 'member':
        return 'bg-green-100 text-green-800 border-green-200 hover:bg-green-100';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200 hover:bg-gray-100';
    }
  };

  const getStatusVariant = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return 'default';
      case 'frozen':
        return 'secondary';
      case 'suspended':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
        return 'bg-emerald-100 text-emerald-800 border-emerald-200 hover:bg-emerald-100';
      case 'frozen':
        return 'bg-cyan-100 text-cyan-800 border-cyan-200 hover:bg-cyan-100';
      case 'suspended':
        return 'bg-rose-100 text-rose-800 border-rose-200 hover:bg-rose-100';
      case 'pending':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200 hover:bg-yellow-100';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200 hover:bg-gray-100';
    }
  };

  const getRoleIcon = (role: string) => {
    switch (role.toLowerCase()) {
      case 'team_leader':
      case 'owner':
        return <Crown className="w-3 h-3" />;
      case 'admin':
        return <Shield className="w-3 h-3" />;
      default:
        return <Users className="w-3 h-3" />;
    }
  };

  const filteredMembers = useMemo(() => {
    const term = debouncedSearch.toLowerCase();
    const base = members.filter((member) => {
      const n = (member.name || '').toLowerCase();
      const e = (member.email || '').toLowerCase();
      const matchesSearch = !term || n.includes(term) || e.includes(term);
      const matchesRole = roleFilter === 'all' || String(member.role).toLowerCase() === roleFilter.toLowerCase();
      return matchesSearch && matchesRole;
    });

    const sorted = [...base].sort((a, b) => {
      const dir = sortDir === 'asc' ? 1 : -1;
      switch (sortKey) {
        case 'email':
          return a.email.localeCompare(b.email) * dir;
        case 'role':
          return String(a.role).localeCompare(String(b.role)) * dir;
        case 'status':
          return String(a.status).localeCompare(String(b.status)) * dir;
        case 'joined':
          return (new Date(a.joined_date).getTime() - new Date(b.joined_date).getTime()) * dir;
        case 'name':
        default:
          return a.name.localeCompare(b.name) * dir;
      }
    });
    return sorted;
  }, [members, debouncedSearch, roleFilter, sortKey, sortDir]);

  const onRetryLoad = useCallback(() => {
    setLoading(true);
    setTimeout(() => setLoading(false), 300); 
    if (currentTeam?.id) {
      (async () => {
        try {
          setError(null);
          if (abortRef.current) { try { abortRef.current.abort(); } catch {} }
          const controller = new AbortController();
          abortRef.current = controller;
          const data = await TeamService.getTeamMembers(currentTeam.id, controller.signal as any);
          setMembers(data);
          toast.success('Members reloaded');
        } catch (err) {
          if ((err as any)?.name === 'AbortError') return;
          setError(err instanceof Error ? err.message : 'Failed to load team members');
          toast.error('Failed to reload members');
        } finally {
          setLoading(false);
        }
      })();
    }
  }, [currentTeam?.id]);

  const toggleSort = useCallback((key: typeof sortKey) => {
    setSortKey((prevKey) => {
      if (prevKey === key) {
        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
        return prevKey;
      }
      setSortDir('asc');
      return key;
    });
  }, []);

  if (!currentTeam) {
    return (
      <Card className="w-full">
        <CardContent className="flex items-center justify-center h-64">
          <div className="text-center space-y-4">
            <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center">
              <AlertCircle className="w-6 h-6 text-muted-foreground" />
            </div>
            <div>
              <h3 className="font-semibold text-lg">No Team Selected</h3>
              <p className="text-muted-foreground text-sm">Please select a team to view members</p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
     

      {/* Error Alert */}
      {error && (
        <Card className="border-destructive/50 bg-destructive/10">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-destructive flex-shrink-0 mt-0.5" />
              <div className="space-y-1 flex-1">
                <h3 className="font-semibold text-destructive">Error Loading Members</h3>
                <p className="text-sm text-destructive/80">{error}</p>
                <div className="pt-2">
                  <Button variant="outline" size="sm" onClick={onRetryLoad}>
                    Retry
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Members Table */}
      <Card>
        <CardHeader className="px-4 -mt-2">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="text-xl">Team Members</CardTitle>
              <CardDescription className="text-xs mt-0.5">
                {filteredMembers.length} member{filteredMembers.length !== 1 ? 's' : ''} 
              </CardDescription>
            </div>
            <div className="flex flex-col sm:flex-row gap-2 sm:items-center w-full sm:w-auto justify-end">
              <div className="flex-1 sm:flex-initial relative sm:w-56">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
                <Input
                  placeholder="Search members..."
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  className="pl-8 h-8 text-sm"
                  aria-label="Search team members"
                />
              </div>
              <div className="flex items-center gap-2 ">
                <Filter className="w-3.5 h-3.5 text-muted-foreground" />
                <Select value={roleFilter} onValueChange={setRoleFilter}>
                  <SelectTrigger className="h-8 text-sm">
                    <SelectValue placeholder="Filter by role" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Roles</SelectItem>
                    <SelectItem value="team_leader">Team Leader</SelectItem>
                    <SelectItem value="admin">Admin</SelectItem>
                    <SelectItem value="member">Member</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <Button
                onClick={() => router.push('/workspace/invite')}
                className="bg-brand-500 hover:bg-brand-600 text-white"
              >
                Invite Member
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent className="pt-0 px-4 -mt-4">
          {loading ? (
            <div className="p-4">
              <div className="rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead className="w-[280px] text-xs">Member</TableHead>
                      <TableHead className="text-xs">Email</TableHead>
                      <TableHead className="text-xs">Role</TableHead>
                      <TableHead className="text-xs">Status</TableHead>
                      <TableHead className="text-xs">Joined</TableHead>
                      <TableHead className="text-xs">Permissions</TableHead>
                      <TableHead className="w-[50px]"></TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {Array.from({ length: 5 }).map((_, i) => (
                      <TableRow key={i}>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <Skeleton className="h-8 w-8 rounded-full" />
                            <div className="space-y-1.5 w-full max-w-[220px]">
                              <Skeleton className="h-3.5 w-2/3" />
                            </div>
                          </div>
                        </TableCell>
                        <TableCell><Skeleton className="h-5 w-48" /></TableCell>
                        <TableCell><Skeleton className="h-5 w-20 rounded-full" /></TableCell>
                        <TableCell><Skeleton className="h-5 w-16 rounded-full" /></TableCell>
                        <TableCell><Skeleton className="h-3.5 w-20" /></TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Skeleton className="h-5 w-20 rounded-full" />
                            <Skeleton className="h-5 w-24 rounded-full" />
                          </div>
                        </TableCell>
                        <TableCell><Skeleton className="h-7 w-7 rounded-md" /></TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </div>
          ) : filteredMembers.length === 0 ? (
            <div className="flex items-center justify-center h-64 text-center">
              <div className="space-y-4">
                <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center">
                  <Users className="w-6 h-6 text-muted-foreground" />
                </div>
                <div>
                  <h3 className="font-semibold text-lg">
                    {searchTerm || roleFilter !== "all" ? "No members found" : "No team members"}
                  </h3>
                  <p className="text-muted-foreground text-sm mt-1">
                    {searchTerm || roleFilter !== "all" 
                      ? "Try adjusting your search or filter criteria"
                      : "Get started by inviting team members"
                    }
                  </p>
                </div>
              </div>
            </div>
          ) : (
            <div className="rounded-md border overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-[280px]">
                      <button className="flex items-center gap-1 text-sm hover:underline" onClick={() => toggleSort('name')}>
                        Member <span className="text-xs">{sortKey === 'name' && (sortDir === 'asc' ? '▲' : '▼')}</span>
                      </button>
                    </TableHead>
                    <TableHead>
                      <button className="flex items-center gap-1 text-sm hover:underline" onClick={() => toggleSort('email')}>
                        Email <span className="text-xs">{sortKey === 'email' && (sortDir === 'asc' ? '▲' : '▼')}</span>
                      </button>
                    </TableHead>
                    <TableHead>
                      <button className="flex items-center gap-1 text-sm hover:underline" onClick={() => toggleSort('role')}>
                        Role <span className="text-xs">{sortKey === 'role' && (sortDir === 'asc' ? '▲' : '▼')}</span>
                      </button>
                    </TableHead>
                    <TableHead>
                      <button className="flex items-center gap-1 text-sm hover:underline" onClick={() => toggleSort('status')}>
                        Status <span className="text-xs">{sortKey === 'status' && (sortDir === 'asc' ? '▲' : '▼')}</span>
                      </button>
                    </TableHead>
                    <TableHead>
                      <button className="flex items-center gap-1 text-sm hover:underline" onClick={() => toggleSort('joined')}>
                        Joined <span className="text-xs">{sortKey === 'joined' && (sortDir === 'asc' ? '▲' : '▼')}</span>
                      </button>
                    </TableHead>
                    <TableHead>
                      <span className="text-sm">Permissions</span>
                    </TableHead>
                    <TableHead className="w-[50px]"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredMembers.map((member) => (
                    <TableRow key={member.id} className="group">
                      <TableCell className="py-2.5">
                        <div className="flex items-center gap-3">
                          <Avatar className="h-8 w-8">
                            <AvatarFallback className="bg-gradient-to-br from-blue-500 to-brand-600 text-white">
                              {member.name.charAt(0).toUpperCase()}
                            </AvatarFallback>
                          </Avatar>
                          <div className="flex flex-col">
                            <span className="font-medium text-sm leading-5">{member.name}</span>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="py-2.5">
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <Mail className="w-3 h-3" />
                          <span className="truncate max-w-[220px]">{member.email}</span>
                        </div>
                      </TableCell>
                      <TableCell className="py-2.5">
                        <Badge 
                          variant={getRoleVariant(member.role)} 
                          className={`gap-1.5 px-2 py-0.5 text-[11px] ${getRoleColor(member.role)}`}
                        >
                          {getRoleIcon(member.role)}
                          {member.role.replace('_', ' ')}
                        </Badge>
                      </TableCell>
                      <TableCell className="py-2.5">
                        <Badge 
                          variant={getStatusVariant(member.status)} 
                          className={`px-2 py-0.5 text-[11px] ${getStatusColor(member.status)}`}
                        >
                          {member.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="py-2.5">
                        <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                          <Calendar className="w-3 h-3" />
                          {new Date(member.joined_date).toLocaleDateString()}
                        </div>
                      </TableCell>
                      <TableCell className="py-2.5">
                        <div className="flex flex-wrap gap-2">
                          {member.permissions?.can_manage_team && (
                            <Badge className="px-2 py-0.5 text-[11px] bg-purple-100 text-purple-800 border-purple-200">Manage Team</Badge>
                          )}
                          {member.permissions?.can_invite && (
                            <Badge className="px-2 py-0.5 text-[11px] bg-blue-100 text-blue-800 border-blue-200">Invite</Badge>
                          )}
                          {member.permissions?.can_edit && (
                            <Badge className="px-2 py-0.5 text-[11px] bg-emerald-100 text-emerald-800 border-emerald-200">Edit</Badge>
                          )}
                          {member.permissions?.can_delete && (
                            <Badge className="px-2 py-0.5 text-[11px] bg-rose-100 text-rose-800 border-rose-200">Delete</Badge>
                          )}
                          {!member.permissions && (
                            <span className="text-xs text-muted-foreground">No permissions info</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="py-2.5">
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="icon" className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity" aria-label={`Actions for ${member.name}`}>
                              <MoreVertical className="w-4 h-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuItem disabled={!canManageMembers}>View Profile</DropdownMenuItem>
                            <DropdownMenuItem disabled={!canManageMembers}>Edit Role</DropdownMenuItem>
                            <DropdownMenuItem className="text-destructive" disabled={!canManageMembers}>
                              Remove Member
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

     
    </div>
  );
}