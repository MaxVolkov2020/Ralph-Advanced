import React, { useEffect } from 'react';
import toast, { Toaster } from 'react-hot-toast';
import { io, Socket } from 'socket.io-client';
import { CheckCircle, XCircle, AlertCircle, Info } from 'lucide-react';

let socket: Socket | null = null;

export const NotificationSystem: React.FC = () => {
  useEffect(() => {
    // Connect to WebSocket
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
    socket = io(API_URL, {
      transports: ['websocket'],
      auth: {
        token: localStorage.getItem('token'),
      },
    });

    socket.on('connect', () => {
      console.log('WebSocket connected');
    });

    socket.on('notification', (data: any) => {
      showNotification(data.type, data.message);
    });

    socket.on('story_update', (data: any) => {
      toast.custom((t) => (
        <div className={`${t.visible ? 'animate-enter' : 'animate-leave'} max-w-md w-full bg-white shadow-lg rounded-lg pointer-events-auto flex ring-1 ring-black ring-opacity-5`}>
          <div className="flex-1 w-0 p-4">
            <div className="flex items-start">
              <div className="ml-3 flex-1">
                <p className="text-sm font-medium text-gray-900">
                  Story Update
                </p>
                <p className="mt-1 text-sm text-gray-500">
                  {data.story_name} - {data.status}
                </p>
              </div>
            </div>
          </div>
          <div className="flex border-l border-gray-200">
            <button
              onClick={() => toast.dismiss(t.id)}
              className="w-full border border-transparent rounded-none rounded-r-lg p-4 flex items-center justify-center text-sm font-medium text-blue-600 hover:text-blue-500 focus:outline-none"
            >
              Close
            </button>
          </div>
        </div>
      ));
    });

    socket.on('disconnect', () => {
      console.log('WebSocket disconnected');
    });

    return () => {
      if (socket) {
        socket.disconnect();
        socket = null;
      }
    };
  }, []);

  return (
    <Toaster
      position="bottom-right"
      toastOptions={{
        duration: 4000,
        style: {
          background: '#fff',
          color: '#363636',
        },
      }}
    />
  );
};

export const showNotification = (type: 'success' | 'error' | 'warning' | 'info', message: string) => {
  const icons = {
    success: <CheckCircle className="w-5 h-5 text-green-600" />,
    error: <XCircle className="w-5 h-5 text-red-600" />,
    warning: <AlertCircle className="w-5 h-5 text-yellow-600" />,
    info: <Info className="w-5 h-5 text-blue-600" />,
  };

  toast.custom((t) => (
    <div className={`${t.visible ? 'animate-enter' : 'animate-leave'} max-w-md w-full bg-white shadow-lg rounded-lg pointer-events-auto flex ring-1 ring-black ring-opacity-5`}>
      <div className="flex-1 p-4">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            {icons[type]}
          </div>
          <div className="ml-3 flex-1">
            <p className="text-sm font-medium text-gray-900">
              {message}
            </p>
          </div>
          <div className="ml-4 flex-shrink-0 flex">
            <button
              onClick={() => toast.dismiss(t.id)}
              className="inline-flex text-gray-400 hover:text-gray-500 focus:outline-none"
            >
              <span className="sr-only">Close</span>
              <XCircle className="h-5 w-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  ));
};
