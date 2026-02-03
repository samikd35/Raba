'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import { ProfilesEnumsAPI } from '@/lib/api/cofounderService';
import type { EnumResource, EnumItem, EnumItemPayload } from '@/types/cofounder';
import { toast } from 'react-hot-toast';
import { Search, Plus, Edit2, Trash2, Power, PowerOff, X } from 'lucide-react';

type ResourceTab = {
  key: EnumResource;
  label: string;
};

const RESOURCE_TABS: ResourceTab[] = [
  { key: 'industries', label: 'Industries' },
  { key: 'responsibilities', label: 'Responsibilities' },
  { key: 'commitment', label: 'Commitment' },
  { key: 'venture_stages', label: 'Venture Stages' },
  { key: 'languages', label: 'Languages' },
];

type ModalMode = 'create' | 'edit' | null;

const EnumsManagement: React.FC = () => {
  const router = useRouter();
  const [activeResource, setActiveResource] = useState<EnumResource>('industries');
  const [items, setItems] = useState<EnumItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [showInactiveOnly, setShowInactiveOnly] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [totalItems, setTotalItems] = useState(0);
  const itemsPerPage = 15;

  // Modal state
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [editingItem, setEditingItem] = useState<EnumItem | null>(null);
  const [formData, setFormData] = useState<EnumItemPayload>({
    name: '',
    description: '',
    is_active: true,
  });

  // Fetch items
  const fetchItems = async () => {
    setLoading(true);
    try {
      const response = await ProfilesEnumsAPI.adminListEnums(activeResource, {
        search: searchQuery || undefined,
        isActive: showInactiveOnly ? false : undefined,
        page: currentPage,
        pageSize: itemsPerPage,
      });
      setItems(response.data);
      setTotalItems(response.total);
    } catch (error: any) {
      toast.error(`Failed to fetch ${activeResource}: ${error.message}`);
      setItems([]);
      setTotalItems(0);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchItems();
  }, [activeResource, searchQuery, showInactiveOnly, currentPage]);

  // Reset to first page when changing filters
  useEffect(() => {
    setCurrentPage(1);
  }, [activeResource, searchQuery, showInactiveOnly]);

  // Handle create
  const handleCreate = async () => {
    if (!formData.name.trim()) {
      toast.error('Name is required');
      return;
    }

    try {
      await ProfilesEnumsAPI.createEnumItem(activeResource, formData);
      toast.success(`${formData.name} created successfully`);
      closeModal();
      fetchItems();
    } catch (error: any) {
      toast.error(`Failed to create: ${error.message}`);
    }
  };

  // Handle update
  const handleUpdate = async () => {
    if (!editingItem || !formData.name.trim()) {
      toast.error('Name is required');
      return;
    }

    try {
      await ProfilesEnumsAPI.updateEnumItem(activeResource, editingItem.id, formData);
      toast.success(`${formData.name} updated successfully`);
      closeModal();
      fetchItems();
    } catch (error: any) {
      toast.error(`Failed to update: ${error.message}`);
    }
  };

  // Handle activate/deactivate
  const handleToggleActive = async (item: EnumItem) => {
    try {
      if (item.is_active) {
        await ProfilesEnumsAPI.deactivateEnumItem(activeResource, item.id);
        toast.success(`${item.name} deactivated`);
      } else {
        await ProfilesEnumsAPI.activateEnumItem(activeResource, item.id);
        toast.success(`${item.name} activated`);
      }
      fetchItems();
    } catch (error: any) {
      toast.error(`Failed to toggle status: ${error.message}`);
    }
  };

  // Handle delete
  const handleDelete = async (item: EnumItem) => {
    if (!confirm(`Are you sure you want to permanently delete "${item.name}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await ProfilesEnumsAPI.deleteEnumItem(activeResource, item.id);
      toast.success(`${item.name} deleted permanently`);
      fetchItems();
    } catch (error: any) {
      toast.error(`Failed to delete: ${error.message}`);
    }
  };

  // Modal helpers
  const openCreateModal = () => {
    setFormData({ name: '', description: '', is_active: true });
    setEditingItem(null);
    setModalMode('create');
  };

  const openEditModal = (item: EnumItem) => {
    setFormData({
      name: item.name,
      description: item.description,
      is_active: item.is_active,
    });
    setEditingItem(item);
    setModalMode('edit');
  };

  const closeModal = () => {
    setModalMode(null);
    setEditingItem(null);
    setFormData({ name: '', description: '', is_active: true });
  };

  const totalPages = Math.ceil(totalItems / itemsPerPage);

  return (
    <div className="p-6">
      {/* Header with Toggle */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Cofounder Management
          </h1>

          {/* Toggle Switch */}
          <div className="flex items-center gap-2 bg-white dark:bg-gray-800 p-1 rounded-lg border border-gray-200 dark:border-gray-700">
            <button
              onClick={() => router.push('/admin/cofounder-moderation')}
              className="px-4 py-2 rounded text-sm border border-blue-light-300 font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              Moderation
            </button>
            <button
              className="px-4 py-2 rounded text-sm font-medium bg-brand-500 text-white"
            >
              Enums
            </button>

            <button
                onClick={() => router.push('/admin/reports-monitoring')}
                className="px-4 py-2 rounded text-sm font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              >
                Reports Monitoring
              </button>
          </div>
        </div>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Manage enumerated options for cofounder profiles (industries, responsibilities, commitment levels, and venture stages)
        </p>
      </div>

      {/* Resource Tabs */}
      <div className="mb-6 flex gap-2 border-b border-gray-200 dark:border-gray-700">
        {RESOURCE_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveResource(tab.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              activeResource === tab.key
                ? 'border-brand-500 text-brand-600 dark:text-brand-400'
                : 'border-transparent text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Filters and Actions */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
        {/* Search */}
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder={`Search ${activeResource}...`}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-transparent"
          />
        </div>

        {/* Filter and Create */}
        <div className="flex gap-3">
          <button
            onClick={() => setShowInactiveOnly(!showInactiveOnly)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              showInactiveOnly
                ? 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-white border border-gray-300 dark:border-gray-600'
                : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-400 border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700'
            }`}
          >
            {showInactiveOnly ? 'Show All' : 'Show Inactive Only'}
          </button>
          <button
            onClick={openCreateModal}
            className="flex items-center gap-2 px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <Plus className="w-4 h-4" />
            Create New
          </button>
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500"></div>
        </div>
      ) : items.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          No {activeResource} found
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
            <table className="w-full">
              <thead className="bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Name
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Description
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
                {items.map((item) => (
                  <tr key={item.id} className="hover:bg-gray-50 dark:hover:bg-gray-800">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="text-sm font-medium text-gray-900 dark:text-white">
                        {item.name}
                      </div>
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        {item.slug}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-600 dark:text-gray-400 max-w-md truncate">
                        {item.description || '—'}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span
                        className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          item.is_active
                            ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-400'
                            : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-400'
                        }`}
                      >
                        {item.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                      {new Date(item.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => openEditModal(item)}
                          className="p-1.5 text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded transition-colors"
                          title="Edit"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleToggleActive(item)}
                          className={`p-1.5 rounded transition-colors ${
                            item.is_active
                              ? 'text-orange-600 hover:text-orange-700 dark:text-orange-400 dark:hover:text-orange-300 hover:bg-orange-50 dark:hover:bg-orange-900/20'
                              : 'text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300 hover:bg-green-50 dark:hover:bg-green-900/20'
                          }`}
                          title={item.is_active ? 'Deactivate' : 'Activate'}
                        >
                          {item.is_active ? (
                            <PowerOff className="w-4 h-4" />
                          ) : (
                            <Power className="w-4 h-4" />
                          )}
                        </button>
                        <button
                          onClick={() => handleDelete(item)}
                          className="p-1.5 text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 rounded transition-colors"
                          title="Delete (Super Admin only)"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-6 flex items-center justify-between">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                Showing {(currentPage - 1) * itemsPerPage + 1} to{' '}
                {Math.min(currentPage * itemsPerPage, totalItems)} of {totalItems} items
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Previous
                </button>
                <div className="flex items-center gap-1">
                  {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                    <button
                      key={page}
                      onClick={() => setCurrentPage(page)}
                      className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                        currentPage === page
                          ? 'bg-brand-500 text-white'
                          : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'
                      }`}
                    >
                      {page}
                    </button>
                  ))}
                </div>
                <button
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Create/Edit Modal */}
      <AnimatePresence>
        {modalMode && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
            onClick={closeModal}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white dark:bg-gray-900 rounded-lg shadow-xl max-w-md w-full p-6"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold text-gray-900 dark:text-white">
                  {modalMode === 'create' ? 'Create New' : 'Edit'} {activeResource}
                </h2>
                <button
                  onClick={closeModal}
                  className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Name *
                  </label>
                  <input
                    type="text"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                    placeholder="Enter name"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                    Description
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-brand-500 focus:border-transparent"
                    placeholder="Enter description (optional)"
                  />
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="is_active"
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                    className="w-4 h-4 text-brand-500 border-gray-300 rounded focus:ring-brand-500"
                  />
                  <label htmlFor="is_active" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    Active (visible to users)
                  </label>
                </div>
              </div>

              <div className="mt-6 flex gap-3 justify-end">
                <button
                  onClick={closeModal}
                  className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  onClick={modalMode === 'create' ? handleCreate : handleUpdate}
                  className="px-4 py-2 bg-brand-500 hover:bg-brand-600 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  {modalMode === 'create' ? 'Create' : 'Update'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default EnumsManagement;
