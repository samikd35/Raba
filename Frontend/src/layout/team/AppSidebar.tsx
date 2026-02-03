"use client";
import React, { useEffect, useRef, useState, useCallback, useMemo } from "react";
import NavigationLink from "@/components/NavigationLink";
import Image from "next/image";
import { usePathname } from "next/navigation";
import { useSidebar } from "../../context/SidebarContext";
import { sidebarStatusService, SidebarStatus } from '@/services/sidebarStatusService';
import { useAuthStore } from '@/stores/authStore';


import { toast } from "react-hot-toast";
import { HelpCircle, Lightbulb, Rocket, TrendingUp } from "lucide-react";
import {
  BoxCubeIcon,
  ValueProposition,
  Mvp,
  ChevronDownIcon,
  GridIcon,
  PieChartIcon,
  PlugInIcon,
  ProblemDiscovery,
  Market,
  Consultation,
  Team,
  UsersIcon,
  MailIcon,
  CreditCardIcon,
  SettingsIcon,
  GroupIcon,
  EnvelopeIcon,
  DollarLineIcon,
  ChatIcon,
  PencilIcon,
  HorizontaLDots,
  BoltIcon,
  ShootingStarIcon
} from "../../icons/index";
import SidebarWidget from "./SidebarWidget";
import { Separator } from "@/components/ui/separator"

type NavItem = {
  name: string;
  icon: React.ReactNode;
  path?: string;
  subItems?: { name: string; path: string; pro?: boolean; new?: boolean; disabled?: boolean }[];
  disabled?: boolean;
  comingSoon?: boolean;
  special?: boolean;
};

const navItems: NavItem[] = [
  {
    icon: <GridIcon className="w-5 h-5 text-brand-500 transition-colors duration-200 group-hover:text-brand-600 dark:text-brand-200 dark:group-hover:text-brand-300" />,
    name: "Dashboard",
    path: "/team-workspace/dashboard",
  },
  {
    icon: <HelpCircle className="w-5 h-5 text-brand-500 transition-colors duration-200 group-hover:text-brand-600 dark:text-brand-200 dark:group-hover:text-brand-300 flex-shrink-0" />,
    name: "Problem Discovery",
    subItems: [
      { name: "Problem Validator", path: "/team-workspace/problem-validator", pro: false }
      // ,{ name: "Problem Predictor", path: "/team-workspace/idea-refiner", pro: false }
      // ,{ name: "Problem Explorer", path: "/team-workspace/problem-explorer", pro: false }
    ],
  },


  {
    icon: <Lightbulb className="w-5 h-5 text-brand-500 transition-colors duration-200 group-hover:text-brand-600 dark:text-brand-200 dark:group-hover:text-brand-300 flex-shrink-0" />,
    name: "Value Proposition Design",
    subItems: [
      { name: "Customer Understanding", path: "/team-workspace/projects", pro: false }
      , { name: "Market Findings Analysis", path: "/team-workspace/projects-questionnaire-completed", pro: false }
    ],
  },

  {
    icon: <Rocket className="w-5 h-5 text-brand-500 transition-colors duration-200 group-hover:text-brand-600 dark:text-brand-200 dark:group-hover:text-brand-300 flex-shrink-0" />,
    name: "MVP & BM Development",
    subItems: [
      { name: "Business Model Innovation", path: "/team-workspace/projects-mvp", pro: false }
      , { name: "Product Requirement", path: "/team-workspace/product-requirement/projects", pro: false }
    ],
  },
  // {
  //   icon: <TrendingUp className="w-5 h-5 text-brand-500 transition-colors duration-200 group-hover:text-brand-600 dark:text-brand-200 dark:group-hover:text-brand-300 flex-shrink-0" />,
  //   name: "Market Validation",
  //   path: "/team-workspace/market-validation",
  // },



  {
    icon: <TrendingUp className="w-5 h-5 text-brand-500 transition-colors duration-200 group-hover:text-brand-600 dark:text-brand-200 dark:group-hover:text-brand-300 flex-shrink-0" />,
    name: "Market Validation",
    subItems: [
      { name: "Ask Yuba AI Expert", path: "/team-workspace/projects-project-chat", pro: false }
      // , { name: "Product Requirement", path: "/team-workspace/product-requirement/projects", pro: false }
    ],
  },
  {
    icon: <GridIcon className="w-5 h-5 text-brand-500 transition-colors duration-200 group-hover:text-brand-600 dark:text-brand-200 dark:group-hover:text-brand-300" />,
    name: "Choose Workspaces",
    path: "/choose-workspace",
    special: true,
  },

  {
    icon: <GroupIcon className="w-5 h-5 text-blue-500 transition-colors duration-200 group-hover:text-blue-600 dark:text-blue-400 dark:group-hover:text-blue-300 flex-shrink-0" />,
    name: "Team Members",
    path: "/team-workspace/members",
  },
  {
    icon: <EnvelopeIcon className="w-5 h-5 text-green-500 transition-colors duration-200 group-hover:text-green-600 dark:text-green-400 dark:group-hover:text-green-300 flex-shrink-0" />,
    name: "Invite Members",
    path: "/team-workspace/invite",
  },
  {
    icon: <DollarLineIcon className="w-5 h-5 text-purple-500 transition-colors duration-200 group-hover:text-purple-600 dark:text-purple-400 dark:group-hover:text-purple-300 flex-shrink-0" />,
    name: "Request Credits",
    path: "/team-workspace/credit-requests",
  },
  // {
  //   icon: <Team className="w-5 h-5 text-orange-500 transition-colors duration-200 group-hover:text-orange-600 dark:text-orange-400 dark:group-hover:text-orange-300 flex-shrink-0" />,
  //   name: "Cofounder Matching",
  //   subItems: [
  //     { name: "My Profile", path: "/team-workspace/cofounder-matching/dashboard", pro: false },
  //     { name: "Create/Edit Profile", path: "/team-workspace/cofounder-matching", pro: false },
  //     { name: "Browse Cofounders", path: "/team-workspace/cofounder-matching/browse", pro: false }
  //   ],
  // },
  {
    icon: <ChatIcon className="w-5 h-5 text-teal-500 transition-colors duration-200 group-hover:text-teal-600 dark:text-teal-400 dark:group-hover:text-teal-300 flex-shrink-0" />,
    name: "Book consultation",
    path: "/team-workspace/book-a-consultation",
  },
  {
    icon: <HorizontaLDots className="w-5 h-5 text-gray-500 transition-colors duration-200 group-hover:text-gray-600 dark:text-gray-400 dark:group-hover:text-gray-300 flex-shrink-0" />,
    name: "Settings",
    path: "/team-workspace/settings",
  },
  // {
  //   icon: <CalenderIcon />,
  //   name: "Calendar",
  //   path: "/calendar",
  // },


  // {
  //   name: "Forms",
  //   icon: <ListIcon />,
  //   subItems: [{ name: "Form Elements", path: "/form-elements", pro: false }],
  // },
  // {
  //   name: "Tables",
  //   icon: <TableIcon />,
  //   subItems: [{ name: "Basic Tables", path: "/basic-tables", pro: false }],
  // },

];

const othersItems: NavItem[] = [
  {
    icon: <PieChartIcon />,
    name: "Charts",
    subItems: [
      { name: "Line Chart", path: "/line-chart", pro: false },
      { name: "Bar Chart", path: "/bar-chart", pro: false },
    ],
  },
  {
    icon: <BoxCubeIcon />,
    name: "UI Elements",
    subItems: [
      { name: "Alerts", path: "/alerts", pro: false },
      { name: "Avatar", path: "/avatars", pro: false },
      { name: "Badge", path: "/badge", pro: false },
      { name: "Buttons", path: "/buttons", pro: false },
      { name: "Images", path: "/images", pro: false },
      { name: "Videos", path: "/videos", pro: false },
    ],
  },
  {
    icon: <PlugInIcon />,
    name: "Authentication",
    subItems: [
      { name: "Sign In", path: "/signin", pro: false },
      { name: "Sign Up", path: "/signup", pro: false },
    ],
  },
];


const AppSidebar: React.FC = () => {
  const { isExpanded, isMobileOpen, isHovered, setIsHovered } = useSidebar();
  const { user } = useAuthStore()

  const pathname = usePathname();

  const separatorIndices = [0, 4, 5, 7]; // Define separator positions for maintainability

  // Sidebar unlock status from unified endpoint
  const [sidebarStatus, setSidebarStatus] = useState<SidebarStatus | null>(null);

  // Fetch sidebar status on mount (single API call replaces 4 separate calls)
  useEffect(() => {
    let isMounted = true;

    const loadSidebarStatus = async () => {
      try {
        const status = await sidebarStatusService.getSidebarStatus();
        if (isMounted) {
          setSidebarStatus(status);
          if (process.env.NODE_ENV === "development") {
            console.log("[TeamAppSidebar] Sidebar status loaded:", {
              max_level: status.max_level,
              has_projects: status.has_projects,
            });
          }
        }
      } catch (error) {
        if (process.env.NODE_ENV === "development") {
          console.error("[TeamAppSidebar] Failed to fetch sidebar status:", error);
        }
      }
    };

    loadSidebarStatus();

    return () => {
      isMounted = false;
    };
  }, []);

  // Derive unlock flags from sidebar status
  const unlockFlags = useMemo(() => {
    if (!sidebarStatus) {
      return {
        customerUnderstanding: false,
        marketFindingsAnalysis: false,
        businessModelInnovation: false,
        productRequirement: false,
        askYubaAIExpert: false,
      };
    }
    return sidebarStatusService.getUnlockFlags(sidebarStatus);
  }, [sidebarStatus]);

  // Filter navItems based on user's tenant_type and unlock status
  const filteredNavItems = useMemo(() => {
    const baseNavItems =
      user?.tenant_type === "team"
        ? navItems
        : navItems.filter((item) => item.name !== "Team Members");

    return baseNavItems.map((item) => {
      // Handle Value Proposition Design menu
      if (item.name === "Value Proposition Design" && item.subItems) {
        return {
          ...item,
          subItems: item.subItems.map((subItem) => {
            // Customer Understanding - unlocked when project created
            if (subItem.path === "/team-workspace/projects") {
              return {
                ...subItem,
                disabled: !unlockFlags.customerUnderstanding,
              };
            }

            // Market Findings Analysis - unlocked when questionnaires completed
            if (subItem.path === "/team-workspace/projects-questionnaire-completed") {
              return {
                ...subItem,
                disabled: !unlockFlags.marketFindingsAnalysis,
              };
            }

            return subItem;
          }),
        };
      }

      // Handle MVP & BM Development menu
      if (item.name === "MVP & BM Development" && item.subItems) {
        return {
          ...item,
          subItems: item.subItems.map((subItem) => {
            // Business Model Innovation - unlocked when value map completed
            if (subItem.path === "/team-workspace/projects-mvp") {
              return {
                ...subItem,
                disabled: !unlockFlags.businessModelInnovation,
              };
            }

            // Product Requirement - unlocked when BMC v2 completed
            if (subItem.path === "/team-workspace/product-requirement/projects") {
              return {
                ...subItem,
                disabled: !unlockFlags.productRequirement,
              };
            }

            return subItem;
          }),
        };
      }

      // Handle Market Validation menu
      if (item.name === "Market Validation" && item.subItems) {
        return {
          ...item,
          subItems: item.subItems.map((subItem) => {
            // Ask Yuba AI Expert - unlocked when MVP requirements (Product Requirement) completed
            if (subItem.path === "/team-workspace/projects-project-chat") {
              return {
                ...subItem,
                disabled: !unlockFlags.askYubaAIExpert,
              };
            }

            return subItem;
          }),
        };
      }

      return item;
    });
  }, [user?.tenant_type, unlockFlags]);

  const [openSubmenu, setOpenSubmenu] = useState<{
    type: "main" | "others";
    index: number;
  } | null>(null);
  const [subMenuHeight, setSubMenuHeight] = useState<Record<string, number>>(
    {}
  );
  const subMenuRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const isActive = useCallback((path: string) => path === pathname, [pathname]);

  const handleSubmenuToggle = useCallback((index: number, menuType: "main" | "others") => {
    setOpenSubmenu((prevOpenSubmenu) => {
      if (
        prevOpenSubmenu &&
        prevOpenSubmenu.type === menuType &&
        prevOpenSubmenu.index === index
      ) {
        return null;
      }
      return { type: menuType, index };
    });
  }, []);

  const handleComingSoonClick = useCallback((itemName: string) => {
    toast.success(`${itemName} - Coming Soon! 🚀`, {
      duration: 3000,
      position: 'top-right',
    });
  }, []);

  const renderMenuItems = useCallback((
    navItems: NavItem[],
    menuType: "main" | "others"
  ) => (
    <ul className="flex flex-col gap-2">
      {navItems.map((nav, index) => (
        <li key={`${menuType}-${nav.name}-${index}`}>
          {nav.subItems ? (
            <button
              onClick={() => !nav.disabled && handleSubmenuToggle(index, menuType)}
              className={`menu-item group  ${openSubmenu?.type === menuType && openSubmenu?.index === index
                  ? "menu-item-active"
                  : "menu-item-inactive"
                } ${nav.disabled ? "opacity-75 cursor-default" : "cursor-pointer"} ${!isExpanded && !isHovered
                  ? "lg:justify-center"
                  : "lg:justify-start"
                }`}
              disabled={nav.disabled}
            >
              <span
                className={` ${openSubmenu?.type === menuType && openSubmenu?.index === index
                    ? "menu-item-icon-active"
                    : "menu-item-icon-inactive"
                  }`}
              >
                {nav.icon}
              </span>
              {(isExpanded || isHovered || isMobileOpen) && (
                <span className={`menu-item-text`}>{nav.name}</span>
              )}
              {(isExpanded || isHovered || isMobileOpen) && (
                <ChevronDownIcon
                  className={`ml-auto w-5 h-5 transition-transform duration-200  ${openSubmenu?.type === menuType &&
                      openSubmenu?.index === index
                      ? "rotate-180 text-brand-500"
                      : ""
                    }`}
                />
              )}
            </button>
          ) : nav.comingSoon ? (
            <button
              onClick={() => handleComingSoonClick(nav.name)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 opacity-60
                ${!isExpanded && !isHovered && !isMobileOpen ? "justify-center" : ""}`}
            >
              <span className="flex-shrink-0">
                {nav.icon}
              </span>
              {(isExpanded || isHovered || isMobileOpen) && (
                <>
                  <span className="text-sm font-medium flex-1 text-left">{nav.name}</span>
                  <span className="inline-flex items-center rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 text-[10px] px-1.5 py-0.5 font-semibold uppercase tracking-wide">
                    New
                  </span>
                </>
              )}
            </button>
          ) : nav.special && nav.path ? (
            <NavigationLink
              href={nav.path}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-200 bg-transparent border-2 border-brand-200 text-brand-600 dark:text-brand-400 hover:bg-brand-50 dark:hover:bg-brand-950 hover:border-brand-600 dark:hover:border-brand-400 transform hover:scale-[1.02]
                ${isActive(nav.path) ? "bg-brand-100 dark:bg-brand-900 border-brand-200 dark:border-brand-400 text-brand-700 dark:text-brand-300 ring-2 ring-brand-300 ring-offset-2 ring-offset-white dark:ring-offset-gray-900" : ""}
                ${!isExpanded && !isHovered && !isMobileOpen ? "justify-center px-2 py-2.5" : ""}`}
            >
              <span className={`shrink-0 ${isActive(nav.path) ? "text-brand-700 dark:text-brand-300" : "text-brand-600 dark:text-brand-400"}`}>
                {nav.icon}
              </span>
              {(isExpanded || isHovered || isMobileOpen) && (
                <>
                  <span className="text-sm font-medium flex-1 text-left">{nav.name}</span>
                </>
              )}
            </NavigationLink>
          ) : (
            nav.path && (
              <NavigationLink
                href={nav.path}
                className={`menu-item group ${isActive(nav.path) ? "menu-item-active" : "menu-item-inactive"
                  }`}
              >
                <span
                  className={`${isActive(nav.path)
                      ? "menu-item-icon-active"
                      : "menu-item-icon-inactive"
                    }`}
                >
                  {nav.icon}
                </span>
                {(isExpanded || isHovered || isMobileOpen) && (
                  <span className={`menu-item-text`}>{nav.name}</span>
                )}
              </NavigationLink>
            )
          )}
          {nav.subItems && (isExpanded || isHovered || isMobileOpen) && (
            <div
              ref={(el) => {
                subMenuRefs.current[`${menuType}-${index}`] = el;
              }}
              className="overflow-hidden transition-all duration-300"
              style={{
                height:
                  openSubmenu?.type === menuType && openSubmenu?.index === index
                    ? `${subMenuHeight[`${menuType}-${index}`]}px`
                    : "0px",
              }}
            >
              <ul className="mt-2 space-y-1 ml-9">
                {nav.subItems.map((subItem) => (
                  <li key={subItem.name}>
                    {subItem.disabled || !subItem.path ? (
                      <span
                        className="menu-dropdown-item opacity-75 cursor-default text-gray-500 dark:text-gray-400 flex items-center gap-2"
                      >
                        <span className="w-2 h-2 rounded-full bg-current opacity-20" />
                        <span className="flex items-center gap-1">
                          {subItem.name}
                          {(nav.name === "Value Proposition Design" || nav.name === "MVP & BM Development" || nav.name === "Market Validation") && subItem.disabled && (
                            <svg
                              className="w-3 h-3 text-gray-400 dark:text-gray-500"
                              viewBox="0 0 20 20"
                              fill="currentColor"
                              aria-hidden="true"
                            >
                              <path d="M10 2a4 4 0 00-4 4v2H5a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2v-6a2 2 0 00-2-2h-1V6a4 4 0 00-4-4zm-2 6V6a2 2 0 114 0v2H8z" />
                            </svg>
                          )}
                        </span>
                      </span>
                    ) : (
                      <NavigationLink
                        href={subItem.path}
                        className={`menu-dropdown-item flex items-center gap-2 ${isActive(subItem.path)
                            ? "menu-dropdown-item-active"
                            : "menu-dropdown-item-inactive"
                          }`}
                      >
                        <span className="w-2 h-2 rounded-full bg-current opacity-40" />
                        <span className="flex items-center gap-1">
                          {subItem.name}
                        </span>
                        <span className="flex items-center gap-1 ml-auto">
                          {subItem.new && (
                            <span
                              className={`ml-auto ${isActive(subItem.path)
                                  ? "menu-dropdown-badge-active"
                                  : "menu-dropdown-badge-inactive"
                                } menu-dropdown-badge `}
                            >
                              new
                            </span>
                          )}
                          {subItem.pro && (
                            <span
                              className={`ml-auto ${isActive(subItem.path)
                                  ? "menu-dropdown-badge-active"
                                  : "menu-dropdown-badge-inactive"
                                } menu-dropdown-badge `}
                            >
                              pro
                            </span>
                          )}
                        </span>
                      </NavigationLink>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {separatorIndices.includes(index) && (
            <div className="mt-2">
              <Separator />
            </div>
          )}
        </li>

      ))}
    </ul>
  ), [openSubmenu, isExpanded, isHovered, isMobileOpen, isActive, handleSubmenuToggle, handleComingSoonClick, subMenuHeight, separatorIndices]);

  useEffect(() => {
    // Check if the current path matches any submenu item
    let submenuMatched = false;
    ["main", "others"].forEach((menuType) => {
      const items = menuType === "main" ? filteredNavItems : othersItems;
      items.forEach((nav, index) => {
        if (nav.subItems) {
          nav.subItems.forEach((subItem) => {
            if (isActive(subItem.path)) {
              setOpenSubmenu({
                type: menuType as "main" | "others",
                index,
              });
              submenuMatched = true;
            }
          });
        }
      });
    });

    // If no submenu item matches, close the open submenu
    if (!submenuMatched) {
      setOpenSubmenu(null);
    }
  }, [pathname, isActive, filteredNavItems]);

  useEffect(() => {
    // Set the height of the submenu items when the submenu is opened
    if (openSubmenu !== null) {
      const key = `${openSubmenu.type}-${openSubmenu.index}`;
      if (subMenuRefs.current[key]) {
        setSubMenuHeight((prevHeights) => ({
          ...prevHeights,
          [key]: subMenuRefs.current[key]?.scrollHeight || 0,
        }));
      }
    }
  }, [openSubmenu]);

  return (
    <aside
      className={`fixed top-0 left-0 h-screen bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-800 transition-all duration-300 ease-in-out z-50
        ${isExpanded || isMobileOpen || isHovered ? "w-[290px]" : "w-20"}
        ${isMobileOpen ? "translate-x-0" : "-translate-x-full"}
        lg:translate-x-0`}
      onMouseEnter={() => !isExpanded && setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="flex flex-col h-full">
        {/* Sidebar Logo / Brand - match TeamWorkspaceLayout styling */}
        <div className="h-16 flex items-center px-4 border-b border-gray-200 dark:border-gray-800">
          <NavigationLink href="/">
            {isExpanded || isHovered || isMobileOpen ? (
              <>
                <Image
                  className="dark:hidden"
                  src="/images/logo/logo.svg"
                  alt="Logo"
                  width={110}
                  height={20}
                  priority
                />
                <Image
                  className="hidden dark:block"
                  src="/images/logo/logo-dark.png"
                  alt="Logo"
                  width={110}
                  height={20}
                  priority
                />
              </>
            ) : (
              <Image
                src="/images/logo/logo-icon.png"
                alt="Logo"
                width={32}
                height={32}
                className="mx-auto"
                priority
              />
            )}
          </NavigationLink>
        </div>

        {/* Navigation Menu - align spacing/scroll with TeamWorkspaceLayout */}
        <div className="flex-1 flex flex-col">
          <nav className="flex-1 overflow-y-auto p-3 space-y-6 [-ms-overflow-style:'none'] [scrollbar-width:'none'] [&::-webkit-scrollbar]:hidden">
            <div className="space-y-4">
              <div className="mt-1">
                {renderMenuItems(filteredNavItems, "main")}
              </div>

              {/* <div className="">
                <h2
                  className={`mb-4 text-xs uppercase flex leading-[20px] text-gray-400 ${
                    !isExpanded && !isHovered
                      ? "lg:justify-center"
                      : "justify-start"
                  }`}
                >
                  {isExpanded || isHovered || isMobileOpen ? (
                    "Others"
                  ) : (
                    <HorizontaLDots />
                  )}
                </h2>
                {renderMenuItems(othersItems, "others")}
              </div> */}
            </div>
          </nav>

          {/* {isExpanded || isHovered || isMobileOpen ? <SidebarWidget /> : null} */}
        </div>
      </div>
    </aside>
  );
};

export default AppSidebar;
