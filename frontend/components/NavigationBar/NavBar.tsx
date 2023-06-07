import Link from 'next/link';
import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { deleteCookie } from 'cookies-next';
import { useRouter } from 'next/router';
import { toast } from 'react-toastify';
import { UseLoginStatus } from '@/components/utils/UseLoginStatus';
import UseHasBusinessStatus from '../utils/UseHasBusinessStatus';
import { getCookie } from 'cookies-next';

interface Props {
    isLanding: boolean;
}

type VectorScore = {
    text: string;
    score: string;
};

function NavBar(props: Props) {
    const [color, setColor] = useState('transparent');
    const [textColor, setTextColor] = useState('white');
    const [borderColor, setBorderColor] = useState('transparent');
    const businessStatus = UseHasBusinessStatus();
    const [vectorScores, setVectorScores] = useState<VectorScore[]>([]);

    const router = useRouter();

    const [status, setStatus] = useState(false);

    useEffect(() => {
        if (props.isLanding) {
            const changeColor = () => {
                if (window.scrollY >= 90) {
                    setColor('#f7fafc');
                    setTextColor('#1a202c');
                } else {
                    setColor('transparent');
                    setTextColor('#f7fafc');
                }
            };
            window.addEventListener('scroll', changeColor);
        } else {
            setColor('#f7fafc');
            setTextColor('#1a202c');
            setBorderColor('#e2e8f0');
        }
    }, [props.isLanding]);

    useEffect(() => {
        if (UseLoginStatus()) {
            setStatus(true);
        } else {
            setStatus(false);
        }
    }, [status]);

    useEffect(() => {
        const fetchData = async () => {
            const res = await axios.get<{ userId: string }>(
                process.env.API_URL + '/api/getUserId',
                {
                    headers: {
                        Authorization: `Bearer ${getCookie('token')}`,
                    },
                    withCredentials: true,
                }
            );
            return res.data.userId;
        };

        const fetchUserData = async (userId: string) => {
            const res = await axios.get(
                process.env.API_URL + '/api/profile/' + userId,
                {
                    headers: {
                        Authorization: `Bearer ${getCookie('token')}`,
                    },
                    withCredentials: true,
                }
            );
            return res.data;
        };

        const fetchDataAndUserData = async () => {
            const userId = await fetchData();

            const userData = await fetchUserData(userId);

            const newVectorText = ['Food', 'Pric.', 'Serv.', 'Ambi.', 'Misc.'];

            // cast each userData.vector to a string
            let newVector = userData.vector.map(
                (value: number, index: number) => {
                    return {
                        text: newVectorText[index],
                        score: (value * 100).toFixed(2).toString(),
                    };
                }
            );

            setVectorScores(newVector);
        };

        fetchDataAndUserData();
    }, []);

    return (
        <div
            style={{ backgroundColor: `${color}` }}
            className="fixed left-0 top-0 w-full z-10 ease-in duration-300">
            <div className="max-w-[1240px] m-auto flex flex-row justify-between items-center p-4 text-white">
                <Link href="/">
                    <h1
                        style={{ color: `${textColor}` }}
                        className="font-bold text-4xl">
                        ClickBites
                    </h1>
                </Link>

                {status ? (
                    <ul
                        style={{ color: `${textColor}` }}
                        className="flex flex-row">
                        <li className='px-4'>
                            <div className="flex flex-row">
                                {vectorScores.map((value, index) => (
                                    <div
                                        key={index}
                                        className={`bg-[#f7fafc] border-4 border-gray-200 mx-2 text-xs radial-progress  ${
                                            // if score is less than 0, make text red, else make text green
                                            parseFloat(value.score) < 0
                                                ? 'text-red-500'
                                                : 'text-orange-400'
                                        }`}
                                        style={
                                            {
                                                '--value':
                                                    parseFloat(value.score) < 0
                                                        ? (-parseFloat(
                                                              value.score
                                                          )).toString()
                                                        : value.score,
                                                '--size': '3rem',
                                                '--thickness': '0.3rem',
                                            } as React.CSSProperties
                                        }>
                                        {value.text}
                                    </div>
                                ))}
                            </div>
                        </li>
                        <li className="p-4">
                            {businessStatus == null ? (
                                <div></div>
                            ) : businessStatus ? (
                                <Link href="/dashboard">Dashboard</Link>
                            ) : (
                                <Link
                                    className="bg-gray-900 hover:bg-gray-700 text-white font-semibold py-2 px-4 rounded-md"
                                    href="/registerbusiness">
                                    Register a Business
                                </Link>
                            )}
                        </li>
                        <li className="p-4">
                            <Link href="/profile">Profile</Link>
                        </li>
                        <li className="p-4">
                            <button
                                onClick={() => {
                                    deleteCookie('token');

                                    toast('Log Out succesfully', {
                                        hideProgressBar: true,
                                        autoClose: 2000,
                                        type: 'success',
                                        position: 'bottom-right',
                                    });

                                    setTimeout(() => {
                                        setStatus(!status);
                                        router.push('/');
                                    }, 2100);
                                }}>
                                Log Out
                            </button>
                        </li>
                    </ul>
                ) : (
                    <ul
                        style={{ color: `${textColor}` }}
                        className="flex flex-row">
                        <li className="p-4">
                            <Link href="/login">Log In</Link>
                        </li>
                        <li className="p-4">
                            <Link href="/signup">Sign Up</Link>
                        </li>
                    </ul>
                )}
            </div>
            <hr
                className="border-1 w-full"
                style={{ borderBlockColor: `${borderColor}` }}
            />
        </div>
    );
}

export default NavBar;
