import { useState } from 'react'
import { NavLink, Outlet, useLocation } from 'react-router'
import { BellIcon, BuildingsIcon, SquaresFourIcon, SignOutIcon, ListIcon, ArrowUpRightIcon, CaretRightIcon, UserCircleIcon } from '@phosphor-icons/react'
import { Brand } from '../components/brand'
import { Button, Dialog } from '../components/ui'
import { useAuth } from '../features/auth/AuthProvider'
import { NotificationMenu } from '../features/notifications/NotificationHub'

function Navigation({ close }: { close?: () => void }) {
  return <nav className="navigation" aria-label="Điều hướng chính">
    <p className="navigation__label">KHÔNG GIAN CỦA BẠN</p>
    <NavLink to="/dashboard" onClick={close}><SquaresFourIcon aria-hidden="true" />Tổng quan</NavLink>
    <NavLink to="/profiles" onClick={close}><BuildingsIcon aria-hidden="true" />Tổ chức</NavLink>
    <NavLink to="/notifications" onClick={close}><BellIcon aria-hidden="true" />Thông báo</NavLink>
    <NavLink to="/account" onClick={close}><UserCircleIcon aria-hidden="true" />Tài khoản</NavLink>
  </nav>
}

export function AppLayout() {
  const { user, signOut } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()
  const name = [user?.first_name, user?.last_name].filter(Boolean).join(' ') || user?.username || 'Bạn'
  const initials = name.trim().slice(0, 1).toLocaleUpperCase('vi-VN')
  const section = location.pathname.startsWith('/profiles') ? 'Tổ chức' : location.pathname === '/notifications' ? 'Thông báo' : location.pathname === '/account' ? 'Tài khoản' : 'Tổng quan'
  return <div className="app-shell">
    <a href="#main-content" className="skip-link">Đến nội dung chính</a>
    <aside className="sidebar" aria-label="Thanh bên">
      <Brand light />
      <Navigation />
      <div className="sidebar__note"><span className="sidebar__note-icon" aria-hidden="true">↗</span>
        <p>Cùng một nhóm.<br /><strong>Cùng một nhịp.</strong></p>
        <span>Một nơi cho những điều<br />cả nhóm đang hướng tới.</span>
      </div>
      <div className="sidebar__footer"><span className="sidebar__status" aria-hidden="true" />Không gian cộng tác</div>
    </aside>
    <div className="app-main">
      <div className="topbar">
        <div className="topbar__location">
          <Button variant="ghost" className="mobile-menu" onClick={() => setMenuOpen(true)} aria-label="Mở menu"><ListIcon aria-hidden="true" /></Button>
          <span className="topbar__home">Không gian làm việc</span><CaretRightIcon aria-hidden="true" /><span>{section}</span>
        </div>
        <div className="account">
          {user && <NotificationMenu key={user.id} userId={user.id} />}
          <span className="avatar" aria-hidden="true">{initials}</span>
          <span className="account__name">{name}</span>
          <Button variant="ghost" className="logout-button" onClick={() => void signOut()}><SignOutIcon aria-hidden="true" /><span>Đăng xuất</span></Button>
        </div>
      </div>
      <main id="main-content" className="content" tabIndex={-1}><Outlet context={{ currentUserId: user?.id || '' }} /></main>
      <footer className="app-footer"><span>HustlyTasker</span><span>Đồng hành cùng nhóm của bạn <ArrowUpRightIcon aria-hidden="true" /></span></footer>
    </div>
    <Dialog open={menuOpen} onClose={() => setMenuOpen(false)} title="Điều hướng" className="mobile-drawer"><Brand /><Navigation close={() => setMenuOpen(false)} /></Dialog>
  </div>
}
