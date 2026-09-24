import { useState, useEffect } from 'react';
import { userApi } from '../services/api';
import type { User } from '../types';
import { Users } from 'lucide-react';



const roleColors: Record<string, string> = {
  ADMIN: 'text-red-400 bg-red-500/10 border-red-500/20',
  INVESTIGATOR: 'text-blue-400 bg-blue-500/10 border-blue-500/20',
  FORENSIC_OFFICER: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20',
  LEGAL_OFFICER: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  AUDITOR: 'text-purple-400 bg-purple-500/10 border-purple-500/20',
};

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    userApi.list()
      .then((r) => setUsers(r.data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-3">
          <Users className="w-7 h-7 text-vault-400" /> User Management
        </h1>
        <p className="text-dark-400 text-sm mt-1">{users.length} authorized personnel</p>
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><div className="w-8 h-8 border-4 border-vault-600 border-t-transparent rounded-full animate-spin" /></div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {users.map((u) => (
            <div key={u.id} className="glass-card p-5 hover-lift">
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-full bg-vault-600/20 border border-vault-500/30 flex items-center justify-center flex-shrink-0">
                  <span className="text-lg font-bold text-vault-400">{u.full_name.charAt(0)}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-semibold text-white">{u.full_name}</h3>
                  <p className="text-xs text-dark-400 truncate">{u.email}</p>
                  <div className="mt-2 flex items-center gap-2">
                    <span className={`badge text-xs border ${roleColors[u.role] || 'text-dark-400 bg-dark-600/30 border-dark-500/30'}`}>
                      {u.role.replace('_', ' ')}
                    </span>
                    {u.rank_level ? (
                      <span className="badge text-xs border text-dark-400 bg-dark-600/30 border-dark-500/30">
                        Rank {u.rank_level}
                      </span>
                    ) : null}
                  </div>
                  <div className="mt-2 text-xs text-dark-500">
                    <p>{u.department}</p>
                    <p>Badge: {u.badge_number}</p>
                  </div>
                </div>
                <div className={`w-2 h-2 rounded-full ${u.is_active ? 'bg-emerald-500' : 'bg-red-500'}`} />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
