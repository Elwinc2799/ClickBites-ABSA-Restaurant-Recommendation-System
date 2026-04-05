import React, { useEffect } from 'react';

import NavBar from '@/components/NavigationBar/NavBar';
import Footer from '@/components/Layout/Footer';
import { Background } from '@/components/Background/Background';
import Image from 'next/image';
import axios from 'axios';
import { getCookie } from 'cookies-next';
import { useState } from 'react';
import ReviewCard from '@/components/Review/ReviewCard';
import UpdateUserModal from '@/components/UserDetails/UpdateUserModal';
import UseLoadingAnimation from '@/components/utils/UseLoadingAnimation';
import AspectRadar from '@/components/SharedComponents/AspectRadar';

interface Review {
    _id: string;
    user_id: string;
    business_id: string;
    business_name: string;
    business_city: string;
    stars: number;
    text: string;
    date: string;
}
declare global {
    interface Window {
        my_modal_1: HTMLDialogElement | null;
    }
}

type VectorScore = {
    text: string;
    score: string;
};

function Profile() {
    const [id, setId] = useState('');
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [phone, setPhone] = useState('');
    const [address, setAddress] = useState('');
    const [state, setState] = useState('');
    const [city, setCity] = useState('');
    const [reviewCount, setReviewCount] = useState(0);
    const [stars, setStars] = useState(0);
    const [profilePic, setProfilePic] = useState('');
    const [reviews, setReviews] = useState<Review[]>([
        {
            _id: '',
            user_id: '',
            business_id: '',
            business_name: '',
            business_city: '',
            stars: 0,
            text: '',
            date: '',
        },
    ]);
    const [isLoading, setIsLoading] = useState(true);
    const [vectorScores, setVectorScores] = useState<VectorScore[]>([]);

    // get user id and user data including reviews, vector, and average stars
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
            setIsLoading(true);
            const userId = await fetchData();
            setId(userId);

            const userData = await fetchUserData(userId);

            setName(userData.name);
            setEmail(userData.email);
            setPhone(userData.phone || '');
            setAddress(userData.address || '');
            setState(userData.state || '');
            setCity(userData.city || '');
            const reviewsList = userData.reviews || [];
            setReviewCount(userData.review_count ?? reviewsList.length);
            const avgStars = userData.average_stars ??
                (reviewsList.length > 0
                    ? reviewsList.reduce((sum: number, r: any) => sum + (r.stars || 0), 0) / reviewsList.length
                    : 0);
            setStars(avgStars);
            setProfilePic(userData.profile_pic || '');

            const newVectorText = [
                'Food',
                'Service',
                'Price',
                'Ambience',
                'Miscellaneous',
            ];

            // cast each userData.vector to a string
            let newVector = (userData.preference_vector || userData.vector || []).map(
                (value: number, index: number) => {
                    return {
                        text: newVectorText[index],
                        score: (value * 100).toFixed(2).toString(),
                    };
                }
            );

            setVectorScores(newVector);

            const newReviews = reviewsList.map((userReview: any) => ({
                _id: userReview.review_id || userReview._id || '',
                user_id: userReview.user_id || '',
                business_id: userReview.business_id || '',
                business_name: userReview.business_name || '',
                business_city: userReview.business_city || '',
                stars: userReview.stars || 0,
                text: userReview.text || '',
                date: userReview.created_at || userReview.date || '',
            }));

            setReviews(newReviews);
            setIsLoading(false);
        };
        fetchDataAndUserData();
    }, []);

    return (
        <>
            {isLoading ? (
                <UseLoadingAnimation isLoading={isLoading} />
            ) : (
                <>
                    <NavBar isLanding={true} />
                    <Background color="bg-gray-100">
                        <main className="profile-page">
                            <section className="relative block h-[500px]">
                                <div className="relative">
                                    <Image
                                        src="/images/profile-bg.jpg"
                                        alt="Profile background"
                                        width="0"
                                        height="0"
                                        sizes="100vw"
                                        className="object-cover w-full h-96"
                                    />
                                    <div
                                        id="blackOverlay"
                                        className="absolute top-0 w-full h-full opacity-50 bg-black"
                                    />
                                </div>
                            </section>
                            <section className="relative py-16 bg-blueGray-200">
                                <div className="container mx-auto px-20">
                                    <div className="relative flex flex-col min-w-0 break-words bg-white w-full mb-6 shadow-xl rounded-lg -mt-64">
                                        <div className="absolute right-2 top-4">
                                            <UpdateUserModal
                                                id={id}
                                                name={name}
                                                phone={phone}
                                                address={address}
                                                state={state}
                                                city={city}
                                                profilePic={profilePic}
                                            />
                                        </div>
                                        <div className="px-6">
                                            <div className="flex flex-wrap justify-center">
                                                <div className="w-full lg:w-3/12 px-4 lg:order-2 flex justify-center">
                                                    <div className="absolute top left-1/2 transform -translate-x-1/2 -translate-y-1/2">
                                                        <Image
                                                            alt="Profile picture"
                                                            src={
                                                                profilePic
                                                                    ? `/user_photo/${profilePic}`
                                                                    : '/images/blank-profilepic.jpg' 
                                                            }
                                                            width="0"
                                                            height="0"
                                                            sizes="100vw"
                                                            className="w-44 h-44 object-cover rounded-full border-none shadow-xl"
                                                        />
                                                    </div>
                                                </div>

                                                <div className="flex w-4/12 px-4 order-4 text-right self-center justify-around items-end">
                                                    <div className="mr-4 p-3 text-center">
                                                        <span className="text-xl font-bold block uppercase tracking-wide text-gray-900">
                                                            {reviewCount}
                                                        </span>
                                                        <span className="text-sm text-gray-900">
                                                            Reviews
                                                        </span>
                                                    </div>
                                                    <div className="mr-4 p-3 text-center">
                                                        <span className="text-xl font-bold block uppercase tracking-wide text-gray-900">
                                                            {Number(
                                                                stars.toFixed(2)
                                                            )}
                                                        </span>
                                                        <span className="text-sm text-gray-900">
                                                            Average Stars
                                                        </span>
                                                    </div>
                                                </div>
                                                <div className="px-4 order-1 items-end">
                                                    <div className="flex justify-between py-4 lg:pt-4 pt-8">
                                                        <div className="mr-4 p-3 text-center">
                                                            <span className="text-xl font-bold block tracking-wide text-gray-900">
                                                                {email}
                                                            </span>
                                                            <span className="text-sm text-gray-900">
                                                                Email
                                                            </span>
                                                        </div>
                                                        <div className="mr-4 p-3 text-center">
                                                            <span className="text-xl font-bold block  tracking-wide text-gray-900">
                                                                {phone}
                                                            </span>
                                                            <span className="text-sm text-gray-900">
                                                                Phone
                                                            </span>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="text-center mt-4">
                                                <h3 className="text-4xl font-semibold leading-normal mb-2 text-gray-900">
                                                    {name}
                                                </h3>
                                                <div className="text-lg leading-normal mt-0 mb-2 text-gray-900 font-bold uppercase">
                                                    <i className="fas fa-map-marker-alt mr-2 text-lg text-gray-900"></i>{' '}
                                                    {address}, {city}, {state}
                                                </div>
                                            </div>

                                            <div className="mt-10 py-10 border-t border-gray-300 text-center">
                                                <div className="flex flex-col items-center justify-center">
                                                    <div className="w-full lg:w-9/12 px-4">
                                                        <p className="mb-4 text-2xl font-bold leading-relaxed uppercase text-gray-900">
                                                            Reviews
                                                        </p>
                                                    </div>
                                                    <div className="w-full px-4">
                                                        {reviews.length ===
                                                            0 && (
                                                            <div className="flex flex-col items-center justify-center">
                                                                <p className="mb-4 text-lg font-medium leading-relaxed text-gray-900">
                                                                    No reviews
                                                                    yet
                                                                </p>
                                                            </div>
                                                        )}
                                                        {reviews.map(
                                                            (review, index) => (
                                                                <ReviewCard
                                                                    key={index.toString()}
                                                                    review={
                                                                        review
                                                                    }
                                                                    isUser={
                                                                        true
                                                                    }
                                                                />
                                                            )
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="mt-2 py-10 border-t border-gray-300 text-center">
                                                <div className="flex flex-col items-center justify-center">
                                                    <div className="w-full lg:w-9/12 px-4">
                                                        <p className="mb-4 text-2xl font-bold leading-relaxed uppercase text-gray-900">
                                                            Aspect Analysis
                                                        </p>
                                                    </div>
                                                    <div className="w-full h-full flex justify-center items-center">
                                                        <AspectRadar
                                                            vectorScores={
                                                                vectorScores
                                                            }
                                                            isBusiness={false}
                                                            isUser={true}
                                                        />
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </section>
                        </main>
                    </Background>
                    <Footer />
                </>
            )}
        </>
    );
}

export default Profile;

// display vector scores using radial progress bar
// {vectorScores.map(
//     (value, index) => (
//         <div
//             key={index}
//             className={`border-4 border-gray-200 mx-2 text-xl radial-progress  ${
//                 // if score is less than 0, make text red, else make text green
//                 parseFloat(
//                     value.score
//                 ) < 0
//                     ? 'text-red-500'
//                     : 'text-green-500'
//             }`}
//             style={
//                 {
//                     '--value':
//                         parseFloat(
//                             value.score
//                         ) <
//                         0
//                             ? (-parseFloat(
//                                     value.score
//                                 )).toString()
//                             : value.score,
//                     '--size':
//                         '10rem',
//                     '--thickness':
//                         '1rem',
//                 } as React.CSSProperties
//             }>
//             {value.text}
//         </div>
//     )
// )}
